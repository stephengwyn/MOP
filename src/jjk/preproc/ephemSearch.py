#!/usr/cadc/misc/bin/python
#/*+
#************************************************************************
#****  C A N A D I A N   A S T R O N O M Y   D A T A   C E N T R E  *****
#*
#* (c) <year>.				(c) <year>.
#* National Research Council		Conseil national de recherches
#* Ottawa, Canada, K1A 0R6 		Ottawa, Canada, K1A 0R6
#* All rights reserved			Tous droits reserves
#* 					
#* NRC disclaims any warranties,	Le CNRC denie toute garantie
#* expressed, implied, or statu-	enoncee, implicite ou legale,
#* tory, of any kind with respect	de quelque nature que se soit,
#* to the software, including		concernant le logiciel, y com-
#* without limitation any war-		pris sans restriction toute
#* ranty of merchantability or		garantie de valeur marchande
#* fitness for a particular pur-	ou de pertinence pour un usage
#* pose.  NRC shall not be liable	particulier.  Le CNRC ne
#* in any event for any damages,	pourra en aucun cas etre tenu
#* whether direct or indirect,		responsable de tout dommage,
#* special or general, consequen-	direct ou indirect, particul-
#* tial or incidental, arising		ier ou general, accessoire ou
#* from the use of the software.	fortuit, resultant de l'utili-
#* 					sation du logiciel.
#*
#************************************************************************
#*
#*   Script Name:	ephemSearch.py
#*
#*   Purpose:
#*	Proxy delivering JPEG cutouts of CFHT data. Datasets are CFH12K,
#*	public MegaPrime, CFHTLS elixir and CFHTLS Terapix. Users enter
#*	RA, DEC, cutout radius and filter. 
#*
#*   Date		: Nov 1, 2005
#*
#*   Field SCCS data	: %Z%
#*	Module Name	: %M%
#*	Version Number	: %I%
#*	Release Number	: %R%
#*	Last Updated	: %G%
#*
#*   Programmer		: JJ Kavelaars
#*
#*   Modification History:
#*
#****  C A N A D I A N   A S T R O N O M Y   D A T A   C E N T R E  *****
#************************************************************************
#-*/
#################################
# Import required Python modules
#################################
import sys, os, string, time
sys.path.append("/home/cadc/kavelaar/lib/python")
sys.path.append("/usr/cadc/misc/python-modules")
import RO


#####################################
# look up SYBASE account information
#####################################
import Sybase
db_name = 'cfht'
dbinfo = os.popen('/usr/cadc/local/scripts/dbrc_get SYBASE cfht').read()
user_name = string.split(dbinfo, ' ')[0]
user_passwd = string.split(dbinfo, ' ')[1][:-1]



def htmIndex(ra,dec,htm_level=3):
    """Compute htm index of htm_level at position ra,dec"""
    import re
    if os.uname()[0] == "Linux": javabin = '/opt/java2/bin/java '
    htm_level = htm_level
    verc_htm_cmd = javabin+'-classpath /usr/cadc/misc/htm/htmIndex.jar edu.jhu.htm.app.lookup %s %s %s' % (htm_level, ra, dec)

    for result in os.popen( verc_htm_cmd ).readlines():
        result = result[:-1]
        if re.search("ID/Name cc", result):
            (void, coord ) = result.split("=")
            (void, junk, htm_index) = coord.split(" ")
            return htm_index


################
# set MIME type
################OB

def circTOcutout(wcs,ra,dec,rad):
    """Convert an RA/DEC/RADIUS to an imcopy cutout"""
    (x1,y1)=wcs.rd2xy((ra+rad/2.0,dec-rad/2.0))
    (x2,y2)=wcs.rd2xy((ra-rad/2.0,dec+rad/2.0))
    xl=min(x1,x2)
    xr=max(x1,x2)
    yl=min(y1,y2)
    yu=max(y1,y2)
    
    ### constrain the cutout to be inside the image
    x1=max(xl,1)
    x1=int(min(x1,wcs.naxis1))
    
    x2=max(xr,x1,1)
    x2=int(min(x2,wcs.naxis1))
    
    y1=max(yl,1)
    y1=int(min(y1,wcs.naxis2))
    y2=max(yu,y1,1)
    y2=int(min(y2,wcs.naxis2))

    area=(x2-x1)*(y2-y1)
    cutout="[%d:%d,%d:%d]" % ( x1,x2,y1,y2)

    if not y1<y2 or not x1<x2: cutout=None
    return (cutout, area)

def gather_data(dform):

    import re, string, RO.StringUtil
    cdata = {}


    ########################
    # convert RA and DEC to degrees
    ########################
    dkey={'ra': 'ra_sexg', 'dec': 'dec_sexg', 'cutout': 'cutout_radius'}
    ckey={'ra': 'ra_deg', 'dec': 'dec_deg', 'cutout': 'radius_deg'}

    for param in ['ra', 'dec', 'cutout']:
        sexg = str(dform[dkey[param]].value.replace(' ',':'))
        if RO.StringUtil.checkDMSStr(sexg):
            cdata[ckey[param]]=RO.StringUtil.degFromDMSStr(sexg)
        else:
            try:
                cdata[ckey[param]]=float(sexg)
            except:
                cdata[ckey[param]]=0


    return cdata

def find_images(cdata):
    import os

    intersect_info = {}

    #################################################
    # get datasets that contain cutout circle center
    #################################################
    db = Sybase.connect('SYBASE', user_name, user_passwd, database=db_name)
    dbcmd = """
    SELECT w.file_id,w.ext_no,w.*
    FROM wcsInfo w
      JOIN cfht_received r ON w.dataset_name=r.dataset_name
      JOIN exposure e ON e.expnum=r.expnum
    WHERE w.dataset_name  LIKE '%s'
      AND w.htm_index LIKE '%s%s'
      AND abs(night-%s) < 1 ORDER BY w.file_id
    """ % (cdata['dataset_name'],cdata['htm_index'],'%',cdata['night'])

    c = db.cursor()
    c.execute(dbcmd)
    wcsInfo = c.fetchall()
    import wcsutil

    intersect_dataset = {}
    intersect_extnum = {}
    intersect_cutout={}

    import string
    largest_area_value=-1
    largest_area_dataset=''
    
    for dataset in wcsInfo:
        ### build a WCSObject
        wcsDict={}
        for i,elt in enumerate(dataset):
            wcsDict[string.upper(c.description[i][0])]=elt
        wcs=wcsutil.WCSObject(wcsDict)
        (cutout, area)=circTOcutout(wcs,cdata['RA'],cdata['DEC'],max(0.015,cdata['RADIUS']))
        key=str(dataset[0])+string.zfill(int(dataset[1]),2)
        if cutout==None:
            continue
        if area>largest_area_value:
            largest_area_value = area
            largest_area_dataset = key
            
        intersect_cutout[key]= cutout
        intersect_dataset[key] = str(dataset[0])
        intersect_extnum[key] = str(dataset[1])
        
    c.close()
    db.close()

    ##############################################################
    # construct dictionary of nested dictionaries to be returned
    ##############################################################
    intersect_info['dataset'] = intersect_dataset
    intersect_info['extnum'] = intersect_extnum
    intersect_info['cutout'] = intersect_cutout

    data_ok = -1
    if len(intersect_dataset)>0:
        data_ok = 1

    return largest_area_dataset,intersect_info, data_ok

def generate_url(file_id,extno,cutout,proxy_url= 'http://www.cadc.hia.nrc.gc.ca/authProxy/getData'):
    return "%s?file_id=%s&extno=%d&cutout=%s&archive=CFHT&wcs=corrected" % ( proxy_url,
                                                                             file_id,
                                                                             int(extno),
                                                                             cutout )


def generate_jpeg(form, cdata, intersect_info):
    for key in intersect_info['dataset'].keys():
        aladin_url = proxy_url+'file_id='+intersect_info['dataset'][key]+'&extno='+intersect_info['extnum'][key]+'&cutout='+intersect_info['cutout'][key]
	aladin_url = aladin_url.encode('hex_codec')
        dataset_name = intersect_info['dataset'][key]

        ima_aladin = '/tmp/'+dataset_name+'.bmp.pid'+str(os.getpid())
	if os.access(ima_aladin,0): os.remove(ima_aladin)

	alascript = '/tmp/alascript.pid'+str(os.getpid())
	if os.access( alascript, 0 ): os.remove( alascript)
        try:
            f_alascript = open (alascript,"w" )
            f_alascript.write("grid on\n")
            f_alascript.write("get Local(http://data.cadc.hia.nrc.gc.ca/cadcbin/cfht/cfhtCutout_get?get_url="+aladin_url+","+intersect_info['dataset'][key]+",CADC)\n")
            f_alascript.write(";sync;grid on"+"\n")
            f_alascript.write(";sync;save "+ima_aladin+"\n;quit\n")
            f_alascript.close()
        except:
            sys.stdout.write("Status: 500 Server Failure\n\n")
            return
        
	if str(os.popen('ps -auxg').readlines()).find('Xvfb') == -1:
            xvfb_cmd="/usr/cadc/misc/bin/Xvfb :9 -screen 0 1024x1024x8 -fp /usr/X11R6/lib/X11/fonts/misc/ -ac -pn &"
            status=os.system(xvfb_cmd+" >& /dev/null" )
            if status:
                sys.stdout.write("Status: 500 Server Failure\n\n")
                return

	try:
            ala_cmd = javabin+" -jar /usr/cadc/misc/www/external/applets/aladin/Aladin.jar <"+alascript
            cmd="DISPLAY=localhost:9.0;export DISPLAY; "+ala_cmd
            status=os.system(cmd+" >& /dev/null")
            if status: raise Error
            convert_cmd = "/usr/cadc/misc/bin/convert -normalize "+ima_aladin+" jpeg:-"
            p=os.popen(convert_cmd)
            jpeg_data = p.read()
            status = p.read()
            if status: raise Erorr
            sys.stdout.write("Content-type: image/jpeg\n\n")
            sys.stdout.write(jpeg_data)
            sys.stdout.flush()
	except:
	   sys.stdout.write("Status: 500 Server Failed\n\n")

	if os.access(alascript,0): os.remove(alascript)
        if os.access(ima_aladin,0): os.remove(ima_aladin)
        
	return

def predict(abg,date,obs=568):
    """Run GB's predict using an ABG file as input."""
    import orbfit
    import RO.StringUtil
    (ra,dec,a,b,ang) = orbfit.predict(abg,date,obs)
    obj['RA']=ra
    obj['DEC']=dec
    obj['dRA']=a
    obj['dDEC']=b
    obj['dANG']=ang
    return obj


#####################
#####################
# start main routine
#####################
#####################

if __name__ == '__main__':
    from optparse import OptionParser


    parser=OptionParser()
    parser.add_option("--cutout",
    		      action="store_true",
		      dest="cutout",
		      help="Provide a URL that can be used to retrieve a cutout")
    parser.add_option("--verbose","-v",
                      action="store_true",
                      dest="verbose",
                      help="Provide feedback on what I'm doing")
    parser.add_option("--abg",
                      action="store",
                      help="abg file to use in object prediction (orbfit file)")
    parser.add_option("--date",
                      action="store",
                      help="Date to search for observations on")
    parser.add_option("--sigma",
                      action="store",
                      default=1.0,
                      help="How many sigma from the prediction are you willing to look?")


    (opt,args)=parser.parse_args()
    if not opt.date or not opt.abg:
        parser.print_help()
        parser.error("You must give both an ABG file and a DATE to search for observations on\n")
        sys.exit(0)
    
    import sys, RO.StringUtil
    if opt.verbose:
    	sys.stderr.write("Opening a connection to SYBASE\n")

    db = Sybase.connect('SYBASE', user_name, user_passwd, database=db_name)

    obj=predict(opt.abg,opt.date)
    import string
    date=string.replace(opt.date,' ','/')

    dbcmd="""
    SELECT distinct(r.expnum)
    FROM wcsInfo w  JOIN cfht_received r ON w.dataset_name=r.dataset_name
    WHERE w.htm_index like '%s%s'  ORDER BY expnum
    """ % ( htmIndex(obj['RA'],obj['DEC'],htm_level=5),'%')

    if opt.verbose:
    	sys.stderr.write("Searching Archive for images at correct location using command\n %s\n" % ( dbcmd,))

    c = db.cursor()
    c.execute(dbcmd)
    datasets = c.fetchall()
    if opt.verbose:
    	sys.stderr.write("Found %d images at correct location, checking date of observations\n" % ( len(datasets)))

    dbcmd="SELECT expnum,night FROM exposure where expnum=@expnum and abs(datediff(day,creation_date,'%s'))<1 ORDER BY expnum" % ( date,)
    timeInfo=[]
    for dataset in datasets:
    	constraint={'@expnum': dataset[0]}
	c.execute(dbcmd,constraint)
	night=c.fetchone()
	if night:
	    timeInfo.append((night[0],night[1]))
    if opt.verbose:
    	sys.stderr.write("Found %d possible images at correct location and date\n" % ( len(timeInfo)))
	sys.stderr.write("Now checking the chip boundaries \n")

    c.close()

    import string
    import math
    good_files_found=0
    for row in timeInfo:
        night=str(row[1])
        dataset_name=str(row[0])
        mjdate=2400000.5+int(night)
        obj=predict(opt.abg,mjdate)
        obj['night']=night
        obj['dataset_name']=dataset_name
        obj['htm_index']=htmIndex(obj['RA'],obj['DEC'],htm_level=3)
        obj['RADIUS']=float(opt.sigma)*math.sqrt(obj['dRA']*obj['dRA']+obj['dDEC']*obj['dDEC'])/3600.0
        
        (largest,intersect_info,data_ok)=find_images(obj)
        if data_ok>0:
            for key in intersect_info['dataset'].keys():
                file_id=intersect_info['dataset'][key]
                extno=intersect_info['extnum'][key]
                cutout=intersect_info['cutout'][key]
		if opt.cutout:
		    good_files_found=good_files_found+1
                    cmd=generate_url(file_id,extno,cutout)
		    if opt.verbose:
		    	sys.stderr.write("Getting cutout from the archive using url: %s \n" %( cmd))
		    print cmd
		else:
                    cmd ='getData.pl %s %d ' % ( file_id, int(extno)-1)
		    if opt.verbose:
		    	sys.stderr.write("Getting image from the archive using command %s \n" %( cmd))
		    status=os.system(cmd)
		    if status:
		    	sys.stderr.write("Get data FAILED\n Try manual retrieval of image %s extension %d\n" % ( file_id, extno))
		    else:
		    	sys.stderr.write("Retrieved %s%d.fits\n" % ( file_id, int(extno)-1))
	else:
	    if ( opt.verbose ) :
	        sys.stderr.write("Source is off the field for %s \n" % ( dataset_name, ))
    if good_files_found==0:
        sys.stderr.write("Couldn't find any NEW FILES for the data/abg file combination given\n")
