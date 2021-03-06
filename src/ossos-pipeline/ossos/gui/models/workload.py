from glob import glob
import re
import sys
from ossos import ssos, astrom
from ossos.downloads.async import DownloadRequest
from ossos.downloads.cutouts import ImageCutoutDownloader

__author__ = "David Rusk <drusk@uvic.ca>"

import os
import random
import threading

from ossos.astrom import StreamingAstromWriter
from ossos.gui import tasks, events, config
from ossos.gui import logger
from ossos.gui.models.collections import StatefulCollection
from ossos.gui.models.exceptions import (NoAvailableWorkException,
                                         SourceNotNamedException)
from ossos.gui.progress import FileLockedException
from ossos.orbfit import Orbfit



class WorkUnit(object):
    """
    A unit of work to be processed, associated with the data from a single
    input file.
    """

    def __init__(self, filename,
                 parsed_data,
                 progress_manager,
                 output_context,
                 dry_run=False):
        self.filename = filename
        self.data = parsed_data
        self.progress_manager = progress_manager
        self.output_context = output_context
        self.dry_run = dry_run

        self.sources = StatefulCollection(parsed_data.get_sources())

        self.readings_by_source = {}
        for source in self.sources:
            self.readings_by_source[source] = StatefulCollection(source.get_readings())

        self.processed_items = set()
        self._mark_previously_processed_items()

        if self.is_current_item_processed():
            self.next_item()

        self.finished_callbacks = []

        self._unlocked = False

    def register_finished_callback(self, callback):
        self.finished_callbacks.append(callback)

    def next_source(self):
        self.get_sources().next()

    def previous_source(self):
        self.get_sources().previous()

    def next_obs(self):
        self.get_current_source_readings().next()

    def previous_obs(self):
        self.get_current_source_readings().previous()

    def next_item(self):
        raise NotImplementedError()

    def accept_current_item(self):
        self.process_current_item()

    def reject_current_item(self):
        self.process_current_item()

    def process_current_item(self):
        self.processed_items.add(self.get_current_item())

        if self.is_current_source_finished():
            self.progress_manager.record_index(self.get_filename(),
                                               self.get_current_source_number())
            self.get_writer().flush()

        if self.is_finished():
            self.progress_manager.record_done(self.get_filename())
            self.unlock()

            for callback in self.finished_callbacks:
                callback(self.get_results_file_paths())

            self._close_writers()

    def get_current_item(self):
        raise NotImplementedError()

    def get_current_item_index(self):
        raise NotImplementedError()

    def is_item_processed(self, item):
        return item in self.processed_items

    def is_current_item_processed(self):
        return self.is_item_processed(self.get_current_item())

    def is_source_finished(self, source):
        raise NotImplementedError()

    def is_current_source_finished(self):
        return self.is_source_finished(self.get_current_source())

    def get_filename(self):
        return self.filename

    def get_data(self):
        return self.data

    def get_sources(self):
        return self.sources

    def get_unprocessed_sources(self):
        unprocessed_sources = []
        for source in self.get_sources():
            if not self.is_source_finished(source):
                unprocessed_sources.append(source)

        return unprocessed_sources

    def get_source_count(self):
        return len(self.get_sources())

    def get_current_source(self):
        return self.get_sources().get_current_item()

    def get_current_source_number(self):
        return self.get_sources().get_index()

    def get_current_source_readings(self):
        return self.readings_by_source[self.get_current_source()]

    def get_obs_count(self):
        return len(self.get_current_source_readings())

    def get_current_reading(self):
        """
        :return: SourceReading
        """
        return self.get_current_source_readings().get_current_item()

    def get_current_obs_number(self):
        return self.get_current_source_readings().get_index()

    def get_writer(self):
        raise NotImplementedError()

    def get_results_file_paths(self):
        raise NotImplementedError()

    def is_finished(self):
        return len(self._get_item_set() - self.processed_items) == 0

    def is_apcor_needed(self):
        raise NotImplementedError()

    def unlock(self):
        if not self._unlocked:
            self.progress_manager.unlock(self.get_filename(), async=True)
            self._unlocked = True

    def _get_item_set(self):
        raise NotImplementedError()

    def _mark_previously_processed_items(self):
        pass

    def _close_writers(self):
        pass


class RealsWorkUnit(WorkUnit):
    """
    A unit of work when performing the process reals task.
    """

    def __init__(self,
                 filename,
                 parsed_data,
                 progress_manager,
                 output_context,
                 dry_run=False):
        super(RealsWorkUnit, self).__init__(
            filename,
            parsed_data,
            progress_manager,
            output_context,
            dry_run=dry_run)

        self._writers = {}

    def next_item(self):
        assert not self.is_finished()

        self.next_obs()
        while self.is_current_item_processed():
            self._next_sequential_item()

    def _next_sequential_item(self):
        """
        Go to the next item in the 'ideal' processing sequence.
        """
        if self.get_current_source_readings().is_on_last_item():
            self.next_source()
        else:
            self.next_obs()

    def get_current_item(self):
        return self.get_current_reading()

    def get_current_item_index(self):
        return (self.get_sources().get_index() * self.get_obs_count() +
                self.get_current_source_readings().get_index())

    def is_source_finished(self, source):
        for reading in source.get_readings():
            if reading not in self.processed_items:
                return False

        return True

    def is_apcor_needed(self):
        return True

    def get_writer(self):
        filename = self.get_output_filename(self.get_current_source())
        if filename in self._writers:
            return self._writers[filename]

        writer = self._create_writer(filename)
        self._writers[filename] = writer
        return writer

    def get_results_file_paths(self):
        return [self.output_context.get_full_path(filename)
                for filename in self._writers]

    def get_output_filename(self, source):
        if not source.has_provisional_name():
            raise SourceNotNamedException(source)

        return ".".join((os.path.basename(self.filename),
                         source.get_provisional_name(),
                         "mpc"))

    def _create_writer(self, filename):
        # NOTE: this import is only here so that we don't load up secondary
        # dependencies (like astropy) used in MPCWriter when they are not
        # needed (i.e. cands task).  This is to help reduce the application
        # startup time.
        from ossos.mpc import MPCWriter

        return MPCWriter(self.output_context.open(filename),
                         auto_flush=False)

    def _get_item_set(self):
        all_readings = set()
        for readings in self.readings_by_source.itervalues():
            all_readings.update(readings)
        return all_readings

    def _mark_previously_processed_items(self):
        processed_indices = self.progress_manager.get_processed_indices(self.get_filename())
        for index in processed_indices:
            for reading in self.get_sources()[index].get_readings():
                self.processed_items.add(reading)

    def _close_writers(self):
        for writer in self._writers.values():
            writer.close()


class CandidatesWorkUnit(WorkUnit):
    """
    A unit of work when performing the process candidates task.
    """

    def __init__(self,
                 filename,
                 parsed_data,
                 progress_manager,
                 output_context,
                 dry_run=False):
        super(CandidatesWorkUnit, self).__init__(
            filename,
            parsed_data,
            progress_manager,
            output_context,
            dry_run=dry_run)

        self._writer = None

    def next_item(self):
        assert not self.is_finished()

        self.next_source()
        while self.is_current_item_processed():
            self.next_source()

    def get_current_item(self):
        return self.get_current_source()

    def get_current_item_index(self):
        return self.get_sources().get_index()

    def is_source_finished(self, source):
        return source in self.processed_items

    def is_apcor_needed(self):
        return False

    def get_writer(self):
        if self._writer is None:
            self._writer = self._create_writer()

        return self._writer

    def get_results_file_paths(self):
        if self._writer is None:
            return []

        return [self.output_context.get_full_path(self._writer.get_filename())]

    def get_output_filename(self):
        return self.get_filename().replace(tasks.get_suffix(tasks.CANDS_TASK),
                                           tasks.get_suffix(tasks.REALS_TASK))

    def _create_writer(self):
        filename = self.get_output_filename()
        return StreamingAstromWriter(self.output_context.open(filename),
                                     self.data.sys_header)

    def _get_item_set(self):
        return set(self.sources)

    def _mark_previously_processed_items(self):
        processed_indices = self.progress_manager.get_processed_indices(self.get_filename())
        for index in processed_indices:
            self.processed_items.add(self.get_sources()[index])

    def _close_writers(self):
        if self._writer is not None:
            self._writer.close()


class TracksWorkUnit(WorkUnit):
    """
    A unit of work when performing the process track task.
    """


    def __init__(self,
                 builder,
                 filename,
                 parsed_data,
                 progress_manager,
                 output_context,
                 dry_run=False):
        super(TracksWorkUnit, self).__init__(
            filename,
            parsed_data,
            progress_manager,
            output_context,
            dry_run=dry_run)

        self.builder = builder
        self._writer = None
        self._ssos_queried = False
        self._comparitors = {}

    def print_orbfit_info(self):
        #TODO: this should not be here.
        print Orbfit(self.get_writer().get_chronological_buffered_observations())

    def query_ssos(self):
        """
        Use the MPC file that has been built up in processing this work
        unit to generate another workunit.
        """
        self._ssos_queried = True
        self.get_writer().flush()
        mpc_filename = self.output_context.get_full_path(self.get_writer().get_filename())
        self.get_writer().close()
        return self.builder.build_workunit(mpc_filename)

    def is_finished(self):
        return self._ssos_queried or self.get_source_count() == 0 or super(TracksWorkUnit, self).is_finished()

    def next_item(self):
        assert not self.is_finished()

        self.next_obs()
        while self.is_current_item_processed():
            self._next_sequential_item()

    def _next_sequential_item(self):
        """
        Go to the next item to process.
        """
        if self.get_current_source_readings().is_on_last_item():
            self.next_source()
        else:
            self.next_obs()

    def get_current_item(self):
        return self.get_current_reading()

    def get_current_item_index(self):
        return (self.get_sources().get_index() * self.get_obs_count() +
                self.get_current_source_readings().get_index())

    def is_source_finished(self, source):
        for reading in source.get_readings():
            if reading not in self.processed_items:
                return False

        return True

    def is_apcor_needed(self):
        return True

    def get_writer(self):
        """
        Get a writer.

        This method also makes the output filename be the same as the .track file but with .mpc.
        (Currently only works on local filesystem)
        """
        if self._writer is None:
            suffix = tasks.get_suffix(tasks.TRACK_TASK)
            try:
                base_name = re.search("(?P<base_name>.*?)\.\d*{}".format(suffix),self.filename).group('base_name')
            except:
                base_name = os.path.splitext(self.filename)[0]
            mpc_filename_pattern = self.output_context.get_full_path(
                "{}.?{}".format(base_name, suffix))
            mpc_file_count = len(glob(mpc_filename_pattern))
            mpc_filename = self.output_context.get_full_path(
                "{}.{}{}".format(base_name, mpc_file_count,suffix))
            self._writer = self._create_writer(mpc_filename)

        return self._writer

    def get_results_file_paths(self):
        if self._writer is None:
            return []

        return [self.output_context.get_full_path(self._writer.get_filename())]

    def _create_writer(self, filename):
        # NOTE: this import is only here so that we don't load up secondary
        # dependencies (like astropy) used in MPCWriter when they are not
        # needed (i.e. cands task).  This is to help reduce the application
        # startup time.
        from ossos.mpc import MPCWriter

        writer = MPCWriter(self.output_context.open(filename),
                           auto_flush=False, auto_discovery=False)

        # Load the input observations into the writer
        for rawname in self.data.mpc_observations:
            writer.write(self.data.mpc_observations[rawname])
        
        return writer

    def _get_item_set(self):
        all_readings = set()
        for readings in self.readings_by_source.itervalues():
            all_readings.update(readings)
        return all_readings

    def _mark_previously_processed_items(self):
        processed_indices = self.progress_manager.get_processed_indices(self.get_filename())
        for index in processed_indices:
            for reading in self.get_sources()[index].get_readings():
                self.processed_items.add(reading)

    def _close_writers(self):
        if self._writer is not None:
            self._writer.close()


class WorkUnitProvider(object):
    """
    Obtains new units of work for the application.
    """

    def __init__(self,
                 taskid,
                 directory_context,
                 progress_manager,
                 builder,
                 randomize=False,
                 name_filter=None):
        self.taskid = taskid
        self.directory_context = directory_context
        self.progress_manager = progress_manager
        self.builder = builder
        self.randomize = randomize
        self.name_filter = name_filter
        self._done = []
        self._already_fetched = []

    @property
    def directory(self):
        """
        The directory that workunits are being acquired from.
        """
        return self.directory_context.directory

    def _filter(self, filename):
        """
        return 'true' if filename doesn't match name_filter regex and should be filtered out of the list.
        @param filename:
        @return:
        """
        return self.name_filter is not None and re.search(self.name_filter,filename) is None

    def get_workunit(self, ignore_list=None):
        """
        Gets a new unit of work.

        Args:
          ignore_list: list(str)
            A list of filenames which should be ignored.  Defaults to None.

        Returns:
          new_workunit: WorkUnit
            A new unit of work that has not yet been processed.  A lock on
            it has been acquired.

        Raises:
          NoAvailableWorkException
            There is no more work available.
        """
        if ignore_list is None:
            ignore_list = []

        potential_files = self.get_potential_files(ignore_list)

        while len(potential_files) > 0:
            potential_file = self.select_potential_file(potential_files)
            potential_files.remove(potential_file)

            if self._filter(potential_file):
                continue

            if self.directory_context.get_file_size(potential_file) == 0:
                continue

            if self.progress_manager.is_done(potential_file):
                self._done.append(potential_file)
                continue
            else:
                try:
                    self.progress_manager.lock(potential_file)
                except FileLockedException:
                    continue

                self._already_fetched.append(potential_file)

                return self.builder.build_workunit(
                    self.directory_context.get_full_path(potential_file))

        logger.info("No eligible workunits remain to be fetched.")

        raise NoAvailableWorkException()

    def get_potential_files(self, ignore_list):
        """
        Get a listing of files for the appropriate task which may or may
        not be locked and/or done.
        """
        return [file for file in self.directory_context.get_listing(self.taskid)
                if file not in ignore_list and
                   file not in self._done and
                   file not in self._already_fetched]

    def select_potential_file(self, potential_files):
        if self.randomize:
            # Don't want predictable patterns in the order we get work units.
            return random.choice(potential_files)
        else:
            return potential_files[0]

    def shutdown(self):
        pass


class PreFetchingWorkUnitProvider(object):
    def __init__(self, workunit_provider, prefetch_quantity, image_manager):
        self.workunit_provider = workunit_provider
        self.prefetch_quantity = prefetch_quantity
        self.image_manager = image_manager

        self.fetched_files = []
        self.workunits = []

        self._threads = []
        self._all_fetched = False

    @property
    def directory(self):
        """
        The directory that workunits are being acquired from.
        """
        return self.workunit_provider.directory

    def get_workunit(self):
        if self._all_fetched and len(self.workunits) == 0:
            raise NoAvailableWorkException()

        if len(self.workunits) > 0:
            workunit = self.workunits.pop(0)
        else:
            workunit = self.workunit_provider.get_workunit(
                ignore_list=self.fetched_files)
            self.fetched_files.append(workunit.get_filename())

        self.trigger_prefetching()
        return workunit

    def trigger_prefetching(self):
        if self._all_fetched:
            return

        num_to_fetch = self.prefetch_quantity - len(self.workunits)

        if num_to_fetch < 0:
            # Prefetch quantity can be 0
            num_to_fetch = 0

        while num_to_fetch > 0:
            if self._all_fetched:
                return

            self.prefetch_workunit()
            num_to_fetch -= 1

    def prefetch_workunit(self):
        thread = threading.Thread(target=self._do_prefetch_workunit)
        self._threads.append(thread)
        thread.start()

    def _do_prefetch_workunit(self):
        try:
            workunit = self.workunit_provider.get_workunit(
                ignore_list=self.fetched_files)
            filename = workunit.get_filename()

            # 2 or more threads created back to back could end up
            # retrieving the same workunit.  Only keep one of them.
            if filename not in self.fetched_files:
                self.fetched_files.append(filename)
                self.workunits.append(workunit)
                self.image_manager.download_singlets_for_workunit(workunit)

                logger.info("%s was prefetched." % filename)

        except NoAvailableWorkException:
            self._all_fetched = True

    def shutdown(self):
        # Make sure all threads are finished so that no more locks are
        # acquired
        for thread in self._threads:
            thread.join()

        for workunit in self.workunits:
            workunit.unlock()


class WorkUnitBuilder(object):
    """
    Used to construct a WorkUnit with its necessary components.
    """

    def __init__(self, parser, input_context, output_context, progress_manager,
                 dry_run=False):
        self.parser = parser
        self.input_context = input_context
        self.output_context = output_context
        self.progress_manager = progress_manager
        self.dry_run = dry_run

    def build_workunit(self, input_fullpath):
        try:
            parsed_data = self.parser.parse(input_fullpath)
        except AssertionError as e:
            logger.critical(str(e))
            events.send(events.NO_AVAILABLE_WORK)
        logger.debug("Parsed %s (%d sources)" %
                     (input_fullpath, parsed_data.get_source_count()))

        _, input_filename = os.path.split(input_fullpath)

        return self._do_build_workunit(
            input_filename,
            parsed_data,
            self.progress_manager,
            self.output_context,
            self.dry_run)

    def _do_build_workunit(self,
                           filename,
                           data,
                           progress_manager,
                           output_context,
                           dry_run):
        raise NotImplementedError()


class TracksWorkUnitBuilder(WorkUnitBuilder):
    """
    Used to construct a WorkUnit for doing 'Track'
    """

    def __init__(self, parser, input_context, output_context, progress_manager,
                 dry_run=False):
        super(TracksWorkUnitBuilder, self).__init__(
            parser, input_context, output_context, progress_manager,
            dry_run=dry_run
        )

    def get_readings(self, data):
        # Note: Track workunits only have 1 source
        return data.get_sources()[0].get_readings()

    def set_readings(self, data, readings):
        # Note: Track workunits only have 1 source
        data.get_sources()[0].readings = readings

    def get_discovery_index(self, data):
        # Note: there should only be one reading marked "discovery" amongst
        # the data.
        for i, reading in enumerate(self.get_readings(data)):
            if reading.discovery:
                return i
        return 1
        raise ValueError("No discovery index found in track workunit.")

    def move_discovery_to_front(self, data):
        """
        Moves the discovery triplet to the front of the reading list.
        Leaves everything else in the same order.
        """
        readings = self.get_readings(data)
        discovery_index = self.get_discovery_index(data)

        reordered_readings = (readings[discovery_index:discovery_index + 3] +
                              readings[:discovery_index] +
                              readings[discovery_index + 3:])

        self.set_readings(data, reordered_readings)

    def _do_build_workunit(self,
                           filename,
                           data,
                           progress_manager,
                           output_context,
                           dry_run):

        # Doesn't work... TODO: FixMe
        # self.move_discovery_to_front(data)

        return TracksWorkUnit(self,
            filename, data, progress_manager, output_context, dry_run=dry_run)


class RealsWorkUnitBuilder(WorkUnitBuilder):
    """
    Used to construct a WorkUnit with its necessary components.
    Constructs RealsWorkUnits for the process reals task.
    """

    def __init__(self, parser, input_context, output_context, progress_manager,
                 dry_run=False):
        super(RealsWorkUnitBuilder, self).__init__(
            parser, input_context, output_context, progress_manager,
            dry_run=dry_run)

    def _do_build_workunit(self,
                           filename,
                           data,
                           progress_manager,
                           output_context,
                           dry_run):
        return RealsWorkUnit(
            filename, data, progress_manager, output_context,
            dry_run=dry_run)


class CandidatesWorkUnitBuilder(WorkUnitBuilder):
    """
    Used to construct a WorkUnit with its necessary components.
    Constructs CandidatesWorkUnits for the process candidates task.
    """

    def __init__(self, parser, input_context, output_context, progress_manager,
                 dry_run=False):
        super(CandidatesWorkUnitBuilder, self).__init__(
            parser, input_context, output_context, progress_manager,
            dry_run=dry_run)

    def _do_build_workunit(self,
                           filename,
                           data,
                           progress_manager,
                           output_context,
                           dry_run):
        return CandidatesWorkUnit(
            filename, data, progress_manager, output_context,
            dry_run=dry_run)
