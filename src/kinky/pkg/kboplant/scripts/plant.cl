#  pcfh99I.cl  modification of cfhtp.cl from B. Gladman and JJ. Kavelaars
# 
# Modification history:
# July 21/00 Kavelaars: set so that it uses the hans.shifts file and the
# 			the file-list
#
# Mar 28/00 Kavelaars: modified to add moving objects in small steps 
#	  	       to simulate possible trailing losses.
#
# Mar 26/99 Petit: modified to allow magnitude variation of reference star
#                  and uses PSFs for each image.
#
#   Plants fake objects in N images at a random rate and direction.
#  Accesses the image headers to get the exposure start time.  User
#
#  Input requirements: There must be N(=nimg) REGISTERED image named xxxxn
#      with xxxx being the common file name and  n sequential.
#
#  Reference star is one chosen on the object frame with the same AM as the
#  calibrator frame.  Magnitude variations are computed for this ref star
#  and all planted stars in each frame are put in with the same magnitude 
#  offset.
#
#  -------->  NOTE:  This script reads the .pst files created by phot.  In
#  building the reference star list one runs phot initially, then pstselect
#  (which creates image.pst.1) and then psf (which creates image.pst.2).  It
#  is this SECOND image (image.pst.2) from which the magnitude of the reference
#  star is taken.  Thus, no other .pst images should exist in this directory.
#

procedure pcfh00xI (common,prefimg,pfieldn,pseed)
        string common {"", prompt=" file-list filename "}
	string prefimg {"", prompt=" name of reference image "}
	string pfieldn {"", prompt=" name of header keyword for obs time "}
	string pexpfield {"", prompt="Exposure time header keyword"}
        int pseed     {"", prompt=" seed number "}
	int pnimg     {"", prompt=" number of aligned images "}
	int pnobjmin  {"", prompt=" minimum number of objects to plant"}
	real pnobjdis  {"", prompt=" max number MORE than min number"}
#       real pfrmsz   {1900, prompt=" frame size (pixels) 100 pix padded to y"}
#	JJK:  replaced if a read of naxis[1] and naxis[2]
        real pratem   {"", prompt=" MEAN rate on sky (pixels/hour)"}
        real pratedis {"", prompt=" rate dispersion (pixels/hour)"}
        real panglem   {"", prompt=" MEAN |angle| (degrees)"}
        real pangledis {"", prompt=" angle dispersion (degrees)"}
	real minmag    {"", prompt="minimum INSTRUMENTAL mag to plant at"}
	real magdis    {"", prompt="max mag FAINTER than min mag"}

	string *pimages, *ppstfiles
begin 
        int    nimg, cpflag, nobj, i, j, nobjmin
        real   rate,xsh0,ysh0,angle,outang, nobjdis
	real   ratedis,angledis,raternd,anglernd
	real   ratem,anglem
        real   xsh,ysh,npix
        real   currtime, strttime, endtime, deltatime
        real   xstart,ystart,mag,rnum,realmag
	real   xss[1500],yss[1500],as[1500],rs[1500],mags[1500]
	real   dx,dy,dist
# xref yref and xpst ypst are for the x,y shifts of non-aligned images JJK
	real   rmag,xfrmsz,yfrmsz,xpst,ypst,xref,yref,tstep
	real   xcen,ycen,refmag,thisrefmag,dmag,thismag,exptime
	int    rseed,dt,nstep
        string infile,rootword,outfile,tfile,dummy
        string objfile,newfield,refimg,fieldn,thisfile,expfield


        cache("utilities.urand")
	cache("daophot")
        cache("digiphot.daophot.addstar")
	
	rootword = common
        pimages = rootword
	refimg = prefimg
	fieldn = pfieldn
	expfield = pexpfield
	rseed  = pseed
	nobjmin = pnobjmin
	nobjdis = pnobjdis
#c      frmsz = pfrmsz
#c	Get the x size and y size seperately JJK 28/03/2000
	i = fscan(pimages,infile)
	imgets(infile,"i_naxis1")
	xfrmsz = real(imgets.value)
	imgets(infile,"i_naxis2")
	yfrmsz = real(imgets.value)
	ratem   = pratem
	ratedis=pratedis
	anglem  = panglem
	angledis=pangledis
	nimg = pnimg

        gettime(infile,fieldn)
        strttime = gettime.outputime

	
        


	if (nobjmin > 150) {nobjdis = 150}
	if (nobjmin+nobjdis > 151) {nobjdis = 151 - nobjmin}
        print(" ")
        print(" CFH Object planting program") 
        print(" ") 
        print(" Input to this program is from N registered images! ")
	i = nobjmin
	j = nobjmin+nobjdis-1
        print(" Plants ", i,"-", j, " objects at given rate with dispersion")
        print(" ") 
        print(" Objects move to upper right! ") 
        print(" ") 

# difference with jjp.cl is that signs removed on next 2 lines
        anglem = anglem/57.29578
        angledis = angledis/57.29578
#        print("  ") 
#        print(" Modifying images: ",rootword) 
#  Removed by JJK 2000/03/27, finally.
#        print(" Will create fkxxxxx frames. Input anything to continue ") 
# Note that this is now a dummy read.
#        scan(cpflag)
	cpflag=1

        print("  ") 
        print(" Working... ") 
	urand(1,1,ndigits=5,seed=rseed,scale_factor=nobjdis) | scan nobj
 	nobj = nobj + nobjmin
        objfile=("Object.list")
	for (i=1; i<=nobj; i+=1) {

	 redo:

	 urand(1,1,ndigits=5,seed=rseed,scale_factor=100000.) | scan rseed
	 urand(1,1,ndigits=5,seed=rseed,scale_factor=magdis) | scan rmag

# compute instrumental mag
# FOR CFH99I all photometry is on standard system, matched to AM of SA98 2 sec.
	 mag = minmag + rmag
	 realmag = mag 
	 urand(1,1,ndigits=5,seed=rseed,scale_factor=100000.) | scan rseed
         urand(1,1,ndigits=5,seed=rseed,scale_factor=xfrmsz) | scan xstart
         urand(1,1,ndigits=5,seed=rseed,scale_factor=100000.) | scan rseed
         urand(1,1,ndigits=5,seed=rseed,scale_factor=yfrmsz) | scan ystart

         urand(1,1,ndigits=5,seed=rseed,scale_factor=100000.) | scan rseed
	 urand(1,1,ndigits=5,seed=rseed) | scan rnum
	 rate = ( 2.0*(rnum-0.5) )*ratedis + ratem
         urand(1,1,ndigits=5,seed=rseed,scale_factor=100000.) | scan rseed
	 urand(1,1,ndigits=5,seed=rseed) | scan rnum
	 angle = ( 2.0*(rnum-0.5) )*angledis + anglem

	 xss[i] = xstart 
	 yss[i] = ystart 
	 mags[i] = mag
	 rs[i] = rate
	 as[i] = angle
#		print(" xss",i," =",xstart,"      mag=",mag)
	   for (j=1; j<i; j+=1)
	   {
		dx = xss[i] - xss[j]
		dy = yss[i]-yss[j]
		dist = dx*dx + dy*dy
		if (dist < 1.0) {
	     print(" PANIC! Duplicate i",i," and j",j," Redoing last object.")
		   goto redo
		}
		;
	   }
	   ;
         print(xss[i],yss[i],realmag,rate,57.3*angle, >> objfile)
	}

#        print("KILL shell if any PANICs appear above. Enter to 1 continue") 
# Note that this is now a dummy read.
#        scan(cpflag)
#	if (cpflag != 1) print ("ERROR ! ! STOP STOP STOP !!!!")
#--------------------------------------------------------------------------

        print(" ") 
        print(" Object list built.  Processing files: ")
        print(" ") 

	tfile=mktemp("tmp$pt")
	infile = refimg//".pst.2"
# Add read of XCENTER and YCENTER to allow non-alligned images
	pdump(infile,"XCENTER,YCENTER,MAG","yes", >> tfile)
	ppstfiles=tfile
	dummy = fscan(ppstfiles,xref,yref,refmag)
	delete(tfile, verify-)


        print(" **  Image 1 acquired at ", strttime, " UT") 
	pimages = rootword
	while ( fscan(pimages,infile) != EOF ) {
	    
	    imgets(infile,expfield)
	    exptime = real(imgets.value)/3600.0
            outfile = 'fk'//infile
            print("       Currently working on: ",outfile)
            gettime(infile,fieldn)
            currtime = gettime.outputime
            print(" * Image acquired at ", currtime, " UT") 
   	    thisfile = infile//".pst.2"
	    tfile=mktemp("tmp$pt")
            pdump(thisfile,"XCENTER,YCENTER,MAG","yes", >> tfile)
            ppstfiles=tfile
            dummy = fscan(ppstfiles,xpst,ypst,thisrefmag)
	    dx = xref - xpst
	    dy = yref - ypst
	    print (dx,dy) ;
	    delete(tfile, verify-)
	    dmag = thisrefmag - refmag
# This is a sloppy re-use of the objfile variable....but it's OK.
            objfile=mktemp("addstar");
            for (i=1; i<=nobj; i+=1) {
              xsh0 = rs[i]*cos(as[i]) ;
              ysh0 = rs[i]*sin(as[i]) ;
              npix = sqrt(xsh0**2 + ysh0**2)*exptime
              nstep = int(npix+1) ;
#              print(nstep,npix)
              tstep  = exptime/nstep ;
              for (dt=0; dt < nstep ; dt += 1) { 
#  Note - signs (compare findkuiper) have been removed!
                ysh = ysh0*(currtime+dt*tstep - strttime)
                xsh = xsh0*(currtime+dt*tstep - strttime)
# Shift is in the sense - (Xref - Xpst) to get to the frame of pst	
		xsh = xsh + xss[i] - xref + xpst
		ysh = ysh + yss[i] - yref + ypst
		thismag = mags[i] + dmag - 2.5*log10(1.0/nstep)
# Only include if the object doesn't fall off the edge of the frame
          if ( (xsh < xfrmsz+1) && (xsh > 0) && (ysh >0) &&(ysh < yfrmsz))
         	print(xsh,ysh,thismag,i, >> objfile)

	      }
#             print(" xsh0 ",xsh0," and ysh0 ",ysh0) 
#               	print(" xshift ",xsh," and yshift ",ysh) 

            }
	    print(" planting objects in image ")
            addstar(infile,objfile,"default",outfile,simple+,verify-,verbose-)
 	    delete(objfile, verify-)
 	    delete(outfile, verify-)
        
#            newfield = 'I-img-no'
#            hedit(outfile,newfield,(j),add+,show-,update+,verify-)

        }

#        print(" Deleting object file!")
#        delete(objfile, verify-)
        print(" ")
        print(" Done ")
        print(" Object.list EXISTS; gzip it!")
        print(" ")

end
