#!/usr/bin/env python
#*
#*   RCS data:
#*	$RCSfile: search.py,v $
#*	$Revision: 1.9 $
#*	$Date: 2007/05/15 19:40:19 $
#*
#*   Programmer		: JJ Kavelaars
#*
#*   Modification History:
#*
#****  C A N A D I A N   A S T R O N O M Y   D A T A   C E N T R E  *****
# Run J-M.'s and Matt's object finding systems... then intersect the 
# result.  

import sys
import time
sys.path.append('/home/cadc/kavelaar/lib/python')

from myTaskError import TaskError

def searchTriples(expnums,ccd,plant=False):
    """Given a list of exposure numbers, find all the KBOs in that set of exposures"""
    import MOPfits,os 
    import MOPdbaccess
    
    if len(expnums)!=3:
        raise TaskError, "got %d exposures"%(len(expnums))


    ### Some program Constants
    proc_these_files=[]
    if not plant:
        proc_these_files.append("# Files to be planted and searched\n")
        proc_these_files.append("#            image fwhm plant\n")
        
    import string
    import os.path
    filenames=[]
    import pyfits
    for expnum in expnums:
        ### Get the processed images from AD
        if int(ccd)<18:
            cutout="[-*,-*]"
        else:
            cutout="[*,*]"
        filename=MOPfits.adGet(str(expnum)+opt.raw,extno=int(ccd),cutout=cutout)

        if not os.access(filename,os.R_OK):
            sys.stderr.write("Ad Get Failed\n")
            raise TaskError, 'adGet Failed'
	    
	if opt.none:
	    continue
        filename=os.path.splitext(filename)
        filenames.append(filename[0])

    	try: 
            mysql=MOPdbaccess.connect('bucket','cfhls','MYSQL')
            bucket=mysql.cursor()
	except:
            raise TaskError, "mysql failed"
        bucket.execute("SELECT obs_iq_refccd FROM exposure WHERE expnum=%s" , (expnum, ) )
        row=bucket.fetchone()
	mysql.close()
        fwhm=row[0]
        if not fwhm > 0:
            fwhm=1.0

        if not plant:
            #proc_these_files.append("%s %f %s \n" % ( filename[0], fwhm/0.183, 'no'))
	    pstr='NO'
        else:
	    pstr='YES'
            ### since we're planting we need a psf.  JMPMAKEPSF will
            ### update the proc-these-files listing

        ### run the make psf script .. always.  This creates proc-these-files
        ### which is needed by the find.pl script.
        command='jmpmakepsf.csh ./ %s %s' % ( filename[0]+".fits", pstr )

        if opt.verbose:
            sys.stderr.write( command )
        try:
            os.system(command)
        except:
            raise TaskError, "jmpmakepsf noexec"
        if os.access(filename[0]+'.jmpmakepsf.FAILED',os.R_OK) or not os.access(filename[0]+".psf.fits", os.R_OK) :
#	    if plant:
#                raise TaskError, "jmpmakepsf failed"
#	do without plant
            if 1==1 :
	        plant=False
		pstr='NO'
	        ### we're not planting so, lets keep going
		### but check that there is a line in proc_these_files
	        add_line=True
		if not os.access('proc-these-files',os.R_OK):
		    f=open('proc-these-files','w')
		    for l in proc_these_files:
		        f.write(l)
		    f.close()
	    	f=open('proc-these-files','r')
		ptf_lines=f.readlines()
		f.close()
		for ptf_line in ptf_lines:
		    if ptf_line[0]=='#':
		        continue
	            ptf_a=ptf_line.split()
		    import re
		    if re.search('%s' % (filename[0]),ptf_a[0]):
		        ### there's already a line for this one
			add_line=False
		        break
                if add_line:
		    f=open('proc-these-files','a')
		    f.write("%s %f %s \n" % ( filename[0], fwhm/0.183, 'no'))
		    f.close()

    if opt.none:
        return(-1)
    prefix=''
    if plant:
        command="plant.csh ./ -rmin %s -rmax %s -ang %s -width %s " % ( opt.rmin, opt.rmax, opt.angle, opt.width)
        try: 
            os.system(command)
        except:
            raise TaskError, 'plant exec. failed'
        if not os.access('plant.OK',os.R_OK):
            raise TaskError, 'plant failed'
        prefix='fk'
    #else:
    #    f=open('proc-these-files','w')
    #    for line in proc_these_files:
    #        f.write(line)
    #    f.flush()
    #    f.close()
    	
    if opt.rerun and os.access('find.OK',os.R_OK):
        os.unlink("find.OK")

    command="find.pl -p "+prefix+" -rn %s -rx %s -a %s -aw %s -d ./ " % ( opt.rmin, opt.rmax, opt.angle, opt.width) 
    #command="find.pl -p "+prefix+" -d ./ " 
    if opt.verbose:
        sys.stderr.write( command )

    try:
        os.system(command)
    except:
        raise TaskErorr, "execute find"
    

    if not os.access("find.OK",os.R_OK):
        raise TaskError, "find failed"

    ### check the transformation file
    command = "checktrans -p "+prefix
    
    try:
        os.system(command)
    except:
        raise TaskError, "execute checktrans"
    
    if not os.access("checktrans.OK",os.R_OK):
        raise TaskError, "checktrans failed"

    if os.access("BAD_TRANS"+prefix,os.R_OK):
        raise TaskError,"BAD TRANS"
        
    astrom=prefix+filenames[0]+".cands.comb"
    if opt.plant:
        astrom=prefix+filenames[0]+".comb.found"
        try:
            #make sure we have +10 lines in this file
	    lines=file(astrom).readlines()
	    if len(lines)<10:
	       raise TaskError,"Too few Found"
	except:
	    raise TaskError, "Error reading %s" %(astrom)
	    
    
    if os.access(astrom,os.R_OK):
        return(1)
    else:
        return(0)


def get_nailing(expnum,ccd):
    """Get the 'nailing' images associated with expnum"""
    sql="""
    SELECT e.expnum, (e.mjdate - f.mjdate) dt
    FROM bucket.exposure e
    JOIN bucket.exposure f
    JOIN bucket.association b ON b.expnum=f.expnum
    JOIN bucket.association a ON a.pointing=b.pointing AND a.expnum=e.expnum
    WHERE f.expnum=%d
    AND abs(e.mjdate - f.mjdate) > 0.5
    AND abs(e.mjdate - f.mjdate) < 15.0
    ORDER BY abs(e.mjdate-f.mjdate)
    """ % ( expnum )
    try:
        import MOPdbaccess
        mysql=MOPdbaccess.connect('bucket','cfhls',dbSystem='MYSQL')
        bucket=mysql.cursor()
        bucket.execute(sql)
        nailings = bucket.fetchall()
        mysql.close()
	if not os.access("nailing",os.F_OK):
	   os.mkdir("nailing")
	os.chdir("nailing")
        if int(ccd) < 18:
            cutout="[-*,-*]"
        else:
            cutout=None
        import MOPfits
        for nailing in nailings:
            filename=MOPfits.adGet(str(nailing[0])+opt.raw,extno=int(ccd),cutout=cutout)
    except:
        raise TaskError, "get nailing failed"
        

if __name__=='__main__':
        ### Must be running as a script
        import optparse, sys,string
        from optparse import OptionParser

        parser=OptionParser()
        parser.add_option("--verbose","-v",
                          action="store_true",
                          dest="verbose",
                          help="Provide feedback on what I'm doing")
        parser.add_option("--none","-n",
                          action="store_true",
                          dest="none",
                          help="Just get the images, no actual processing")
        parser.add_option("--triple","-t",
                          action="store",
                          type="int",
                          dest="triple",
                          help="Triple to search")
        parser.add_option("--check",
                          action="store_true",
                          dest="check",
                          help="CHECK which exposures  will be run [good for checking for failures]")
        parser.add_option("--nailing",
                          action="store_true",
                          help="Get nailing image?")
        parser.add_option("--skip",
                          action="store_true",
                          help="Skip the triples ?")
        parser.add_option("--epoch","-e",
                          action="store",
                          #default="discovery",
			  default=None,
                          help="Epoch to search.  Choose from [discovery|checkup|recovery]"
                          )
        parser.add_option("--field","-f",
                          action="store",
                          dest="field",
                          help="CFEPS field to search")
        parser.add_option("--block","-b",
                          action="store",
                          dest="block",
			  default=None,
                          help="CFEPS block to search") 
   	parser.add_option("--rmin",action="store",dest="rmin",default=0.5,help="Minimum search rate (''/hr)")			
   	parser.add_option("--rmax",action="store",dest="rmax",default=20,help="Maximum search rate (''/hr)")			
   	parser.add_option("--angle",action="store",dest="angle",default=20,help="ximum search rate (''/hr)")			
   	parser.add_option("--width",action="store",dest="width",default=20,help="ximum search rate (''/hr)")			
        parser.add_option("--ccd","-c",
                          action="store",
                          default=None,
                          type="int",
                          dest="ccd")
        parser.add_option("--plant","-p",
                          action="store_true",
                          default=False,
                          help="Plant artificial objects in the data?"
                          )
        parser.add_option("--move","-m",
                          action="store",
                          default=False,
                          help="Move processed stuff to this directory "
                          )
        parser.add_option("--delete","-d",
                          action="store_true",
                          default=False,
                          help="Delete the images and support files,[for computing detection eff.]"
                          )
        parser.add_option("--raw",
                          action="store_true",
                          default=False,
                          help="Use the raw exposures?")
        parser.add_option("--rerun",
                          action="store_true",
                          default=False,
                          help="Re-run search from scratch"
                          )
	file_ids=[]
        (opt, file_ids)=parser.parse_args()
	if opt.raw:
	    opt.raw="o"
	else:
	    opt.raw="p"

        import os, shutil, sys
        if os.getenv('_CONDOR_SCRATCH_DIR') != None: os.chdir(os.getenv('_CONDOR_SCRATCH_DIR'))

        import MOPdbaccess
        mysql=MOPdbaccess.connect('cfeps','cfhls',dbSystem='MYSQL')
        cfeps=mysql.cursor()
        if opt.verbose:
            print "Starting to gather info about chips to search\n"

        process='search'
        if opt.plant:
            process='plant'

	rerun=""
	if not opt.rerun:
	  rerun=" (p.comment IS NULL OR p.status=-2 ) AND " 
	field=''
	if opt.field:
	  field=" pointings.name LIKE '%s' AND " % ( opt.field ) 
        qname=''
	if opt.block:
	  qname=" b.block LIKE '%s' AND " % ( opt.block ) 
	ccd=""
        if not opt.ccd is None:
	  ccd=" m.ccd=%d AND " % ( int(opt.ccd) ) 
	epoch=""
	if opt.epoch:
	   epoch=""" JOIN """+opt.epoch+""" as d ON d.triple=t.triple """
        if not opt.triple and len(file_ids)==0:
            sql="""SELECT distinct(t.triple),m.ccd 
            FROM triple_members t
	    JOIN triples ON triples.id=t.triple
	    JOIN bucket.pointings pointings ON pointings.id=triples.pointing
            JOIN bucket.blocks b ON b.expnum=t.expnum
	    """+epoch+"""
	    JOIN mosaic m
	    LEFT JOIN processing p ON ( p.triple=t.triple AND p.ccd=m.ccd AND p.process='"""+process+"""')
            WHERE """+rerun+field+qname+ccd+"""
	    m.instrument LIKE 'MEGAPRIME'  
	    order by rand()"""
            
	    if (opt.verbose): 
	        print sql
            cfeps.execute(sql)
            rows=cfeps.fetchall()
        else:
	    rows=[]
            low=0
            high=36
            if opt.ccd is not None:
                low=int(opt.ccd)
                high=int(opt.ccd)+1
            for ccd in range(low,high):
                rows.append([opt.triple,ccd])
            
	mysql.close()
	
	if opt.check:
            mysql=MOPdbaccess.connect('cfeps','cfhls',dbSystem='MYSQL')
            cfeps=mysql.cursor()
	    count=0
	    for row in rows:
	      sys.stdout.write("Doing search on exposures: ")
	      sql="SELECT expnum FROM triple_members where triple=%d" % ( row[0])
	      cfeps.execute(sql)
	      exps=cfeps.fetchall()
	      for exp in exps:
	         sys.stdout.write("%s " %(exp[0]))
              sys.stdout.write("\n")
	    for row in rows:
	       sql="SELECT e.object, %d FROM triple_members m JOIN bucket.exposure e ON  m.expnum=e.expnum LEFT JOIN processing p ON ( p.triple=m.triple AND p.ccd=%d ) WHERE %s m.triple=%d group by e.object " % ( row[1], row[1], rerun, row[0] ) 
	       cfeps.execute(sql)
	       exps=cfeps.fetchall()
	       for exp in exps:
                   if opt.verbose:
                       print exp[0],exp[1]
		   count +=1
            mysql.close()
            if opt.verbose:
                print "Still need to run on %d fields+ccd combos\n" % ( count) 
	    sys.exit(0)

        if opt.verbose:
            sys.stderr.write("Searching %d triples \n" % ( len(rows), ) )

        for row in rows:
            process='search'
            comment='searched'
            started='searching'
            if opt.plant:
                comment='planted'
                process='plant'
                started='planting'
            triple=row[0]
	    ccd=row[1]
            if opt.verbose:
                sys.stderr.write("Working on "+str(triple)+":"+str(ccd)+"\n")
	    ### Grab this row from the list of stuff TBD
            mysql=MOPdbaccess.connect('cfeps','cfhls',dbSystem='MYSQL')
	    while not mysql:
	    	time.sleep(10)
                mysql=MOPdbaccess.connect('cfeps','cfhls',dbSystem='MYSQL')
            cfeps=mysql.cursor()
	    sql="LOCK TABLES processing WRITE"
	    cfeps.execute(sql)
            swhere=" and status != -1 "
            if not opt.rerun:
                swhere=" and status < -1 "
            sql="DELETE FROM processing WHERE triple=%d AND ccd=%d AND process='%s' %s " % ( triple, ccd, process, swhere)
            cfeps.execute(sql)
	    sql="SELECT count(*) FROM processing WHERE triple=%d AND ccd=%d AND process='%s' " % ( triple, ccd, process)
            cfeps.execute(sql)
            scount=cfeps.fetchone()
            if scount[0] > 0 :
                print "Already running %d %d " % ( triple, ccd)
	        cfeps.execute("UNLOCK TABLES")
                continue
            
            sql="INSERT INTO processing (triple, status, comment, ccd, process) VALUES ( %d, %d, '%s', %d, '%s' ) " % ( triple, -1, started, ccd, process)
            cfeps.execute(sql)
            mysql.commit()
	    cfeps.execute("UNLOCK TABLES")
            sql="SELECT e.expnum,e.object FROM triple_members m JOIN bucket.exposure e ON  m.expnum=e.expnum WHERE triple=%d ORDER BY expnum " % ( triple,)
            cfeps.execute(sql)
            exps=cfeps.fetchall()
            mysql.close()
            
            if len(file_ids)==0:
                for exp in exps:
                    file_ids.append(exp[0])
            if opt.verbose:
                sys.stderr.write("Running find on the files "+str(file_ids)+"\n")
	    cwd=os.getcwd()
	    ccdPath=os.path.join("chip"+string.zfill(str(ccd),2),str(exps[0][1]))
            wdir=os.path.join(cwd,ccdPath)
            if opt.verbose:
                print wdir,cwd
	    if not os.path.exists(wdir):
	        os.makedirs(wdir)
            os.chdir(wdir)
            
	    result=-2
            try:
                if opt.verbose :
                    sys.stderr.write("Doing CCD: %s, of files: %s, PLANT: %s\n" %( str(ccd),str(file_ids),str(opt.plant)))
		if not opt.skip:
                    result=searchTriples(file_ids,ccd,opt.plant)
                if result == -1:
                    comment="retreived"
                if opt.nailing:
                    get_nailing(file_ids[0],ccd)
            except TaskError, info:
                sys.stderr.write(str(info))
                comment=str(info)
            os.chdir(cwd)
	    file_ids=[]

	    try:
                if opt.move:
	            #if not os.path.exists(opt.move+"/"+wdir):
		    #    os.makedirs(opt.move+"/"+wdir)
		    #import glob, shutil
		    #for fff in glob.glob("*"):
		    #    shutil.move(fff,opt.move+"/"+wdir+"/"+fff)
	            oscmd="rsync -av %s %s " % ("./" , opt.move)
		    if opt.verbose:
		        sys.stderr.write( "Moving %s to %s \n%s\n" % ( cwd, opt.move, oscmd))
	            status=os.system(oscmd)
		    if status!=0:
		        raise TaskError
                if opt.delete:
                    shutil.rmtree(wdir)
	    except:
	    	comment="FAILED During data moved"

            try:
                mysql=MOPdbaccess.connect('cfeps','cfhls',dbSystem='MYSQL')
                cfeps=mysql.cursor()
                sql="UPDATE processing set comment='%s', status=%d WHERE triple=%d AND ccd=%d and process='%s'" % ( comment, result, triple,ccd,process)
                
                cfeps.execute(sql)
                mysql.commit()
                mysql.close()
            except:
                sys.stderr.write("Update failed\n")
                sys.exit(-1)
            
            if opt.verbose:
                sys.stderr.write("Found %d candidates in triple %d on ccd %d\n" % (result, triple, ccd))
