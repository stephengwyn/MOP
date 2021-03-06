#!/usr/cadc/misc/bin/python
#!/usr/bin/env python

from Tkinter import *
import sys


def myComp(a,b):
    return -1*cmp(a[0],b[0])


mpc_objs={}

def load_edbfile(file=None):
    """Load the targets from a file"""
    import ephem,string,math
    if file is None:
        import tkFileDialog
	try:
            file=tkFileDialog.askopenfilename()
        except:
            return 
    if file is None or file == '':
        return
    f=open(file)
    lines=f.readlines()
    f.close()
    for line in lines:
        p=line.split(',')
	name=p[0].strip().upper()
	mpc_objs[name]=ephem.readdb(line)
	mpc_objs[name].compute()
        objInfoDict[name]="%6s %6s %6s\n" % ( string.center("a",6),
				            string.center("e",6),
	 				    string.center("i",6) ) 
        objInfoDict[name]+="%6.2f %6.3f %6.2f\n" % (mpc_objs[name]._a,mpc_objs[name]._e,math.degrees(mpc_objs[name]._inc))
        objInfoDict[name]+="%7.2f %7.2f\n" % ( mpc_objs[name].earth_distance, mpc_objs[name].mag)
    doplot(mpc_objs)




def load_abgfiles(dir=None):
    """Load the targets from a file"""
    import ephem,string
    if dir is None:
        import tkFileDialog
	try: 
            dir=tkFileDialog.askdirectory()
        except:
            return
    if dir is None:
        return None
    from glob import glob
    files=glob(dir+"/*.abg")
    import os
    for f in files:
        (name,ext)=os.path.splitext(os.path.basename(f))
	NAME=name.strip().upper()
	kbos[name]=f
	#print name
        aei=file(dir+"/"+name+".aei")
        lines=aei.readlines()
        aei.close()
        objInfoDict[name]="%6s %6s %6s\n" % ( string.center("a",6),
				            string.center("e",6),
	 				    string.center("i",6) ) 
        try:
          (a,e,i,N,w,T) = lines[4].split()
        except:
          print lines[4]
          (a,e,i,N,w,T) = (0,0,0,0,0,0)
        objInfoDict[name]+="%6.2f %6.3f %6.2f\n" % (float(a),float(e),float(i))
        s=lines[5][0:2]
        (a,e,i,N,w,T) = lines[5][2:-1].split()
        objInfoDict[name]+=" %6.3f %6.3f %6.3f\n" % (float(a),float(e),float(i))
        abg = file(dir+"/"+name+".abg")
        lines = abg.readlines()
        abg.close()
	for line in lines:
	    if not line[0:5] == "# Bar":
	        continue
            objInfoDict[name]+=line[2:-1]+"\n"
            break
        res=file(dir+"/"+name+".res")
        lines=res.readlines()
        res.close()
        line=lines.pop()
        values=line.split()
        s = "[nobs: "+values[0]+" dt: "+values[1]+"]\n"
        objInfoDict[name]+=s
        mpc = file(dir+"/../mpc/"+name+".mpc")
        lines=mpc.readlines()
        mpc.close()
	last_date=0
	for line in lines:
	    if len(line)==0:
		continue
	    if line[0]=="#":
		continue
            this_year=int(line[15:19])
            this_month=int(line[20:22])
            this_day = int(line[23:25])
	    this_date =  this_year+this_month/12.0 +this_day/365.25
	    if last_date < this_date:
		last_date=this_date
		year=this_year
		day = this_day
		month=this_month	
        mag={}
        for line in lines:
            try:
                mags=line[65:69].strip()
		if len(mags)==0:
		    continue
                filter=line[70]
	        if filter not in mag:
                    mag[filter]=[]
                mag[filter].append(float(mags)) 
	    except:
	        continue
        mags=''
        for filter in mag:
	    magv=0
 	    for m in mag[filter]:
	        magv = magv+m/len(mag[filter]) 
            mags = mags+ "%4.1f-%s " % ( magv , filter)
        if len(mags)==0:
	    mags= "N/A"
        objInfoDict[name]+="MAG: "+mags+"\n"
        objInfoDict[name]+="Last obs: %s %s %s \n" % (year,month, day)

    doplot(kbos)

fits_pointings=[]

def fits_list(filter,root,fnames):
    """Get a list of files matching filter in directory root"""
    import re, pyfits, wcsutil
    for file in fnames:
        if re.match(filter,file):
            fh=pyfits.open(file)
            for ext in fh:
                obj=ext.header.get('OBJECT',file)
                dx=ext.header.get('NAXIS1',None)
                dy=ext.header.get('NAXIS2',None)
                wcs=wcsutil.WCSObject(ext)
                (x1,y1)=wcs.xy2rd((1,1,))
                (x2,y2)=wcs.xy2rd((dx,dy))
                ccds=[x1,y1,x2,y2]
                pointing={'label': obj, 'camera': ccds}
    return files
        
        
def load_fis(dir=None):
    """Load fits images in a directory"""
    if dir is None:
        import tkFileDialog
        try:
            dir=tkFileDialog.askdirectory()
        except:
            return
    if dir is None:
        return None
    from os.path import walk
    walk(dir,fits_list,"*.fits")
    

    
class plot(Canvas):
    """A plot class derived from the the Tkinter.Canvas class"""

    def __init__(self,root,width=640,height=480,background='white'):
        import math,time,ephem,MOPcoord
	
        import Tkinter
        self.heliocentric=Tkinter.StringVar()
        self.heliocentric.set("00:00:00.00 +00:00:00.0")
        self.equatorial=Tkinter.StringVar()
        self.equatorial.set("00:00:00.00 +00:00:00.0")
        self.elongation=Tkinter.StringVar()
        self.ObjInfo=Tkinter.StringVar()
        self.elongation.set("0.0")
        self.SearchVar=Tkinter.StringVar()
        self.FilterVar=Tkinter.StringVar()
        self.FilterVar.set("")
        self.camera=Tkinter.StringVar()
	self.show_ellipse=Tkinter.IntVar()
	self.show_ellipse.set(1)
	self.pointing_format=Tkinter.StringVar()
	self.pointing_format.set('CFHT PH')
	self.show_labels=Tkinter.IntVar()
	self.show_labels.set(1)
	self.date=Tkinter.StringVar()
	self.date.set(time.strftime('%Y/%m/%d'))
	self.plabel=Tkinter.StringVar()
	self.plabel.set("P0")
	sun=ephem.Sun()
        sun.compute(self.date.get())
	self.sun=MOPcoord.coord((sun.ra,sun.dec))
        self.width=width
        self.unit=Tkinter.StringVar()
        self.unit.set('elong')
        self.height=height
        Tkinter.Canvas.__init__(self,root,width=width,height=height,background=background)
        self.tk_focusFollowsMouse()

    def eps(self):
	"""Print the canvas to a postscript file"""

        import tkFileDialog,tkMessageBox
        filename=tkFileDialog.asksaveasfilename(message="save postscript to file",filetypes=['eps','ps'])
	if filename is None:
	    return 

	self.postscript(file=filename)
        
    def newPlot(self):
        import math

        self.rgutter=0
        self.lgutter=0
        self.tgutter=0
        self.bgutter=0
        self.cx1=self.lgutter
        self.cx2=self.width-self.rgutter
        self.cy1=self.height-self.bgutter
        self.cy2=self.tgutter
        self.current=None
	self.limits(2*math.pi,0,-0.5*math.pi,0.5*math.pi)
        self.pointings=[]
	doplot(kbos)

    def p2c(self,p=[0,0]):
        """convert from plot to canvas coordinates.

        See also c2p."""
        
        x=(p[0]-self.x1)*self.xscale+self.cx1
        y=(p[1]-self.y1)*self.yscale+self.cy1

        return (x,y)
    
    def p2s(self,p=[0,0]):
        """Convert from plot to screen coordinates"""

        s=self.p2c(p)
        return self.c2s(s)

    def c2s(self,p=[0,0]):
        """Convert from canvas to screen coordinates"""

        return((p[0]-self.canvasx(self.cx1),p[1]-self.canvasy(self.cy1)))

    def c2p(self,p=[0,0]):
        """Convert from canvas to plot coordinates.

        See also p2s."""
        
        x=(p[0]-self.cx1)/self.xscale+self.x1
        y=(p[1]-self.cy1)/self.yscale+self.y1
        return (x,y)

    def _convert(self,s,factor=15):

	import math
        p = s.split(":")
        h=float(p[0])
 	m=float(p[1])
	s=float(p[2])
	sign=1.0
	if h<0:
	   sign=-1.0
	h=h*sign
        return math.radians(sign*(h+m/60.0+s/3600.0)*factor)

    def hours(self,s):

	return self._convert(s,factor=15.0)

    def degrees(self,s):

	return self._convert(s,factor=360.0)


    def coord_grid(self):
        """Draw a grid of RA/DEC on Canvas."""

        import math,ephem
        ra2=math.pi*2
        ra1=0
        dec1=-1*math.pi/2.0
        dec2=math.pi/2.0

        
        ## grid space choices
        ## ra space in hours
        ra_grids=["06:00:00",
                  "03:00:00",
                  "01:00:00",
                  "00:30:00",
                  "00:15:00",
                  "00:05:00",
                  "00:01:00",
                  "00:00:30",
                  "00:00:15",
                  "00:00:05"]
        dec_grids=["45:00:00",
                   "30:00:00",
                   "15:00:00",
                   "05:00:00",
                   "01:00:00",
                   "00:15:00",
                   "00:05:00",
                   "00:01:00",
                   "00:00:30"]
        dra=(self.x2-self.x1)/3.0
        ddec=(self.y2-self.y1)/3.0
        for ra_grid in ra_grids:
            if self.hours(ra_grid)<math.fabs(dra):
                break
        ra_grid=self.hours(ra_grid)

        for dec_grid in dec_grids:
            if self.degrees(dec_grid)<math.fabs(ddec):
                break
        dec_grid=self.degrees(dec_grid)
        
        ra=ra1
        n=0
        import Tkinter,ephem
        while (ra<=ra2):
            (cx1,cy1)=self.p2c((ra,dec1))
            ly=cy1-30
            (cx2,cy2)=self.p2c((ra,dec2))
            self.create_line(cx1,cy1,cx2,cy2)
            lx=cx1
            n=n+1
            if n==2:
                dec=dec1
                k=2
                while ( dec <= dec2 ):
                    (lx,ly)=self.p2c((ra,dec))
                    (cx1,cy1)=self.p2c((ra1,dec))
                    (cx2,cy2)=self.p2c((ra2,dec))
                    self.create_line(cx1,cy1,cx2,cy2)
                    k=k+1
                    if k==3:
                        self.create_text(lx-45,ly-12,text=str(ephem.hours(ra)),fill='green')
                        self.create_text(lx+40,ly-12,text=str(ephem.degrees(dec)),fill='brown')
                        self.create_point(ra,dec,color='black',size=3)
                        k=0
                    dec=dec+dec_grid
                n=0
            ra=ra+ra_grid

    def eq2ec(self,ra,dec):
	from math import sin
	from math import cos
	import math
	
	sb=math.asin(sin(dec)*cos(math.radians(23.43))-cos(dec)*sin(ra)*sin(math.radians(23.43)))
	sl=math.acos(cos(ra)*cos(dec)/cos(sb))

	return (sb,sl)

    def pos_update(self,event):
        from math import sin
	from math import cos
	import math, MOPcoord


	s=self.sun

        (ra,dec)=self.c2p((self.canvasx(event.x),self.canvasy(event.y)))
	p=MOPcoord.coord((ra,dec))
        elong=math.fabs(p.el-s.el)
	if elong>math.pi:
		elong=2.0*math.pi-elong

	p.set_system('ecliptic')
        self.heliocentric.set(str(p))
	p.set_system('ICRS')
        self.equatorial.set(str(p))
        self.elongation.set("%6.2f" % (math.degrees(elong)))


                
    def helio_grid(self,event):
        import MOPcoord,math,ephem

        
        (ra,dec)=self.c2p((self.canvasx(event.x),self.canvasy(event.y)))
        p = MOPcoord.coord((ra,dec))

        for i in range(0,360):
            a=math.radians(i/1.0)
            t = MOPcoord.coord((a,p.eb),system='ecliptic')
            self.create_point(t.ra,t.dec,size=1,color='magenta')

	for i in range(-90,90):
	    b=math.radians(i/1.0)
	    t = MOPcoord.coord((p.el,b),system='ecliptic')
	    self.create_point(t.ra,t.dec,size=1,color='grey')
            
        
        
    def tickmark(self,x,y,size=10,orientation=90):
        """Draw a line of size and orientation at x,y"""
        import math
        (x1,y1)=self.p2c([x,y])
        x2=x1+size*math.cos(math.radians(orientation))
        y2=y1-size*math.sin(math.radians(orientation))
        self.create_line(x1,y1,x2,y2)
        
    def label(self,x,y,label,offset=[0,0]):
        """Write label at plot coordinates (x,y)"""
        (xc,yc)=self.p2c([x,y])
        return self.create_text(xc-offset[0],yc-offset[1],text=label)
	

    def limits(self,x1,x2,y1,y2):
        """Set the coordinate boundaries of plot"""
        import math
        self.x1=x1
        self.x2=x2
        self.y1=y1
        self.y2=y2
        self.xscale=(self.cx2-self.cx1)/(self.x2-self.x1)
        self.yscale=(self.cy2-self.cy1)/(self.y2-self.y1)

	ra1=self.x1
	ra2=self.x2
	dec1=self.y1
	dec2=self.y2
        (sx1,sy2)=self.p2c((ra1,dec1))
        (sx2,sy1)=self.p2c((ra2,dec2))
	
        
        self.config(scrollregion=(sx1-self.lgutter,sy1+self.bgutter,sx2+self.rgutter,sy2-self.tgutter))

    def reset(self):
        """Expand to the full scale"""

	import ephem, MOPcoord
	
	sun=ephem.Sun()
        sun.compute(self.date.get())
	self.sun=MOPcoord.coord((sun.ra,sun.dec))
        
        doplot(kbos)
        self.plot_pointings()

    def updateObj(self,event):
        """Put this object in the search box"""
        
        name=w.objList.get("active")
        w.SearchVar.set(name)
        w.ObjInfo.set(objInfoDict[name])
        return
    
    def relocate(self):
        """Move to the postion of self.SearchVar"""

        name=self.SearchVar.get()
        if kbos.has_key(name):
	    import orbfit,ephem,math

	    jdate=ephem.julian_date(w.date.get())
 	    try:
	        (ra,dec,a,b,ang)=orbfit.predict(kbos[name],jdate,568)
	    except:
		return
	    ra=math.radians(ra)
	    dec=math.radians(dec)
	elif mpc_objs.has_key(name):
	    ra=mpc_objs[name].ra
	    dec=mpc_objs[name].dec
	self.recenter(ra,dec)
	self.create_point(ra,dec,color='blue',size=4)
            
    def recenter(self,ra,dec):

        x1=ra-(self.x2-self.x1)/2.0
        x2=ra+(self.x2-self.x1)/2.0
        y1=dec-(self.y2-self.y1)/2.0
        y2=dec+(self.y2-self.y1)/2.0
        self.limits(x1,x2,y1,y2)
        import Tkinter
        self.delete(Tkinter.ALL)
        doplot(kbos)

    def center(self,event):
        (ra,dec)=self.c2p((self.canvasx(event.x),self.canvasy(event.y)))
        self.recenter(ra,dec)
        
    def zoom_in(self,event=None):
	
        self.__zoom(event,scale=2.0)

    def zoom_out(self,event=None):
        
        self.__zoom(event,scale=0.5)
        
    def __zoom(self,event,scale=2.0):
        """Zoom in"""

        import Tkinter,math
        ## compute the x,y of the center of the screen
        sx1=self.cx1+(self.cx2-self.cx1+1.0)/2.0
        sy1=self.cy1+(self.cy2-self.cy1+1.0)/2.0
	#print sx1,sy1
	if not event is None:
		sx1=event.x
		sy1=event.y
	#print sx1,sy1
        ## translate that into a canvas location and then
        ## and ra/dec position
        (x,y)=self.c2p((self.canvasx(sx1),self.canvasy(sy1)))
	#print math.degrees(x),math.degrees(y),sx1, sy1
        ## reset the width of the display
        xw=(self.x2-self.x1)/2.0/scale
        yw=(self.y2-self.y1)/2.0/scale

        ## reset the limits to be centered at x,y with
        ## area of xw*2,y2*2
        self.limits(x-xw,x+xw,y-yw,y+yw)

        self.delete(Tkinter.ALL)
        doplot(kbos)

    def create_ellipse(self,xcen,ycen,a,b,ang,resolution=40.0):
        """Plot ellipse at x,y with size a,b and orientation ang"""

        import math
        e1=[]
        e2=[]
        ang=ang-math.radians(90)
        for i in range(0,int(resolution)+1):
            x=(-1*a+2*a*float(i)/resolution)
            y=1-(x/a)**2
            if y < 1E-6:
                y=1E-6
            y=math.sqrt(y)*b
            ptv=self.p2c((x*math.cos(ang)+y*math.sin(ang)+xcen,y*math.cos(ang)-x*math.sin(ang)+ycen))
            y=-1*y
            ntv=self.p2c((x*math.cos(ang)+y*math.sin(ang)+xcen,y*math.cos(ang)-x*math.sin(ang)+ycen))
            e1.append(ptv)
            e2.append(ntv)
        e2.reverse()
        e1.extend(e2)
        self.create_line(e1,fill='red',width=1)

    def create_point(self,xcen,ycen,size=10,color='red'):
        """Plot a circle of size at this x,y location"""

	
        (x,y)=self.p2c((xcen,ycen))
        x1=x-size
        x2=x+size
        y1=y-size
        y2=y+size
        self.create_rectangle(x1,y1,x2,y2,fill=color,outline=color)

    def current_pointing(self,index):
        """set the color of the currently selected pointing to 'blue'"""
        if self.current is not None:
            for item in self.pointings[self.current]['items']:
                self.itemconfigure(item,outline="black")
        self.current=index
        for item in self.pointings[self.current]['items']:
            self.itemconfigure(item,outline="blue")

    def delete_pointing(self,event):
        """Delete the currently active pointing"""

        if self.current is None:
            return
        for item in self.pointings[self.current]['items']:
            self.delete(item)
	self.delete(self.pointings[self.current]['label']['id'])
        del(self.pointings[self.current])
            
        self.current=None

    def get_pointings(self):
        """Query for some pointings, given a block name"""
	import MOPdbaccess,ephem,math
        import tkSimpleDialog
        result = tkSimpleDialog.askstring("Block Load", "Which Block do you want to plot?")
        db = MOPdbaccess.connect('bucket','cfhls',dbSystem='MYSQL')
        SQL = """SELECT object,ra,`dec`,status,ccd FROM blocks b 
			JOIN cfeps.triple_members m ON m.expnum=b.expnum
			JOIN cfeps.discovery d ON d.triple=m.triple
			JOIN exposure e ON e.expnum=b.expnum
                        LEFT JOIN cfeps.processing p ON p.triple=m.triple
		WHERE p.process='plant' and b.block RLIKE '%s' GROUP BY m.triple,p.ccd """ % (result)
	points=[]
	c = db.cursor()
	r = c.execute(SQL)
	rows=c.fetchall()

        print len(rows)
        geo = camera.geometry['MEGACAM_36']
        main_pointing=''
	for row in rows:
            if main_pointing != row[0]:
                # put down the 'full MP FOV' here
                c=camera(camera='MEGACAM_1')
                if row[4]!= "NULL":
                    color='pale green'
                else:
                    color='gray'
                label={'text': row[0]}
                c.ra=ephem.hours(math.radians(float(row[1])))
                c.dec=ephem.degrees(math.radians(float(row[2])))
                self.pointings.append({"label": label,
                                       "camera": c,
                                       "color": color})
                main_pointing=row[0]
            if int(row[3]) < 0:
                # Create a 'red' box for this CCD
                c=camera(camera='MP_CCD')
                c.ra = ephem.hours(math.radians(float(row[1])-geo[int(row[4])]["ra"]/math.cos(math.radians(float(row[2])))))
                c.dec =ephem.degrees(math.radians(float(row[2])-geo[int(row[4])]["dec"]))
                color='red'
                label={'text': str(row[4])}
                self.pointings.append({"label": label, "camera": c,"color":color})
                                       
        self.plot_pointings()

        return
    
    def load_pointings(self):
        """Load some pointings"""
        import os,re,ephem
        import tkFileDialog,tkMessageBox
        filename=tkFileDialog.askopenfilename()
	if filename is None:
	    return 
        f=open(filename)
        lines=f.readlines()
	f.close()
	points=[]
	if lines[0][0:5]=="<?xml":
	    ### assume astrores format
	    ### with <DATA at start of 'data' segment
	    for i in range(len(lines)):
	        if lines[i][0:5]=='<DATA':
		    break
	    for j in range(i+5,len(lines)):
	        if lines[j][0:2]=="]]":
		    break
	        vs=lines[j].split('|')
		points.append(vs)
        elif lines[0][0:5]=='index':
	    ### Palomar Format
	    ### OK.. ID/NAME/RA /DEC format
	    for line in lines:
	        if line[0]=='!' or line[0:5]=='index':
		    # index is a header line for Palomar 
		    continue
	        d = line.split()
	        if len(d)!=9:
	            import sys
	            sys.stderr.write("Don't understand pointing format\n%s\n" %( line))
	            continue
	        ras="%s:%s:%s" % ( d[2],d[3],d[4])
	        decs="%s:%s:%s" % ( d[5],d[6],d[7])
	        points.append((d[1].strip(),ras,decs))
        elif lines[0][0:5]=="#SSIM":
	    ### Survey Simulator format
	    for line in lines[1:]:
		d = line.split()
		points.append((d[8],d[2],d[3]))
        else:
	    ### try name/ ra /dec / epoch
	    for line in lines:
                d=line.split()
	        if len(d)!=4:
                    if len(d)!=8:
	               import sys
	               sys.stderr.write("Don't understand pointing format\n%s\n" %( line))
	               continue
	            line = "%s %s:%s:%s %s:%s:%s %s" % (d[0],d[1],d[2],d[3],d[4],d[5],d[6],d[7] )
		    d=line.split()
 	        import math
                f=d[1].count(":")
	        if ( f > 0 ) :
		    points.append((d[0],d[1],d[2]))
	        else:
		    points.append(('',math.radians(float(d[1])),math.radians(float(d[2]))))

        self.plot_points_list(points)
	return
    
    def plot_points_list(self,points):
        import math, ephem
	for point in points:
	    label={}
	    label['text']=point[0]
            (ra,dec)=(ephem.hours(point[1]),ephem.degrees(point[2]))
            c=camera(camera=self.camera.get())
            ccds=c.getGeometry(float(ra),float(dec))
	    self.pointings.append({"label": label,
				   "camera": c})
            
        self.plot_pointings()
        return

    
    def create_pointing(self,event):
        """Plot the sky coverage of pointing at event.x,event.y on the canavas"""

        import math
        (ra,dec)=self.c2p((self.canvasx(event.x),
                           self.canvasy(event.y)))
        this_camera=camera(camera=self.camera.get())
        ccds=this_camera.getGeometry(ra,dec)
        items=[]
        for ccd in ccds:
            (x1,y1)=self.p2c((ccd[0],ccd[1]))
            (x2,y2)=self.p2c((ccd[2],ccd[3]))
            item=self.create_rectangle(x1,y1,x2,y2)
            items.append(item)
	label={}
	label['text']=w.plabel.get()
	label['id']=self.label(this_camera.ra,this_camera.dec,label['text'])
        self.pointings.append({
		"label": label,
		"items": items,
		"camera": this_camera} )
        self.current_pointing(len(self.pointings)-1)

    def plot_pointings(self,pointings=None):
        """Plot pointings on canavs"""

        if pointings is None:
            pointings=self.pointings

	i=0
        for pointing in pointings:
            items=[]
	    i=i+1
	    label={}
	    label['text']=pointing['label']['text']
            for ccd in pointing["camera"].getGeometry():
                (x1,y1)=self.p2c((ccd[0],ccd[1]))
                (x2,y2)=self.p2c((ccd[2],ccd[3]))
                item=self.create_rectangle(x1,y1,x2,y2,stipple='gray25',fill=pointing.get('color',''))
                items.append(item)
	    if w.show_labels.get()==1:
	        label['id']=self.label(pointing["camera"].ra,pointing["camera"].dec,label['text'])
            pointing["items"]=items
	    pointing["label"]=label


    def set_pointing_label(self):
	    """Let the label of the current pointing to the value in the plabel box"""

	    self.pointings[self.current]['label']['text']=w.plabel.get()
	    self.reset()
	    
    def move_pointing(self,event):
        """Grab nearest pointing to event.x,event.y and with cursor"""


        (ra,dec)=self.c2p((self.canvasx(event.x),
                           self.canvasy(event.y)))
        closest=None
        this_pointing=None
        this_index=-1
        index=-1
        for pointing in self.pointings:
            index=index+1
            # Find the camera we clicked closest too
            ds=pointing["camera"].separation(ra,dec)
            if this_pointing is None or ds < closest:
                this_index=index
                closest=ds
                this_pointing=pointing

	self.plabel.set(this_pointing['label']['text'])
        ccds=this_pointing["camera"].getGeometry(ra,dec)
        items=this_pointing["items"]
	label=this_pointing["label"]
	(x1,y1)=self.p2c((this_pointing["camera"].ra,this_pointing["camera"].dec))
	self.coords(label["id"],x1,y1)
        for i in range(len(ccds)):
            ccd=ccds[i]
            item=items[i]
            (x1,y1)=self.p2c((ccd[0],ccd[1]))
            (x2,y2)=self.p2c((ccd[2],ccd[3]))
            self.coords(item,x1,y1,x2,y2)
        self.current_pointing(this_index)
    
    def clear_pointings(self):
	"""clear the pointings from the display"""

	self.pointings=[]
	doplot(kbos)

    def save_pointings(self):
        """Print the currently defined FOVs"""

        import tkFileDialog
        f=tkFileDialog.asksaveasfile()
        i=0
        if self.pointing_format.get()=='CFHT PH':
	    f.write("""<?xml version = "1.0"?>
<!DOCTYPE ASTRO SYSTEM "http://vizier.u-strasbg.fr/xml/astrores.dtd">
<ASTRO ID="v0.8" xmlns:ASTRO="http://vizier.u-strasbg.fr/doc/astrores.htx">
<TABLE ID="Table">
<NAME>Fixed Targets</NAME>
<TITLE>Fixed Targets for CFHT QSO</TITLE>
<!-- Definition of each field -->
<FIELD name="NAME" datatype="A" width="20">
   <DESCRIPTION>Name of target</DESCRIPTION>
</FIELD>
<FIELD name="RA" ref="" datatype="A" width="11" unit="&quot;h:m:s&quot;">
   <DESCRIPTION>Right ascension of target</DESCRIPTION>
</FIELD>     
<FIELD name="DEC" ref="" datatype="A" width="11" unit="&quot;d:m:s&quot;">
   <DESCRIPTION>Declination of target</DESCRIPTION>
</FIELD>     
<FIELD name="EPOCH" datatype="F" width="6">
    <DESCRIPTION>Epoch of coordinates</DESCRIPTION>
</FIELD>     
<FIELD name="POINT" datatype="A" width="5">
<DESCRIPTION>Pointing name</DESCRIPTION>
</FIELD>     
<!-- Data table --> 
<DATA><CSV headlines="4" colsep="|"><![CDATA[
NAME                |RA         |DEC        |EPOCH |POINT|
                    |hh:mm:ss.ss|+dd:mm:ss.s|      |     |
12345678901234567890|12345678901|12345678901|123456|12345|
--------------------|-----------|-----------|------|-----|\n""")	
        if self.pointing_format.get()=='Palomar':
	    f.write("index\n")
        for pointing in self.pointings:
            i=i+1
            name=pointing["label"]["text"]
            (sra,sdec)=str(pointing["camera"]).split()
	    ra=sra.split(":")
	    dec=sdec.split(":")
	    dec[0]=str(int(dec[0]))
	    if int(dec[0])>=0:
		    dec[0]='+'+dec[0]
	    if self.pointing_format.get()=='Palomar':
		    f.write( "%5d %16s %2s %2s %4s %3s %2s %4s 2000\n" % (i, name,
									  ra[0].zfill(2),
									  ra[1].zfill(2),
									  ra[2].zfill(2),
									  dec[0].zfill(3),
									  dec[1].zfill(2),
									  dec[2].zfill(2)))
	    elif self.pointing_format.get()=='CFHT PH':
                #f.write("%f %f\n" % (pointing["camera"].ra,pointing["camera"].dec))
                f.write("%-20s|%11s|%11s|%6.1f|%-5d|\n" % (name,sra,sdec,2000.0,1))
            elif self.pointing_format.get()=='KPNO/CTIO':
                str1 = sra.replace(":"," ")
	        str2 = sdec.replace(":"," ")
                f.write("%16s %16s %16s 2000\n" % ( name, str1, str2) )
            elif self.pointing_format.get()=='SSim':
                ra = []
 		dec= []
                for ccd in pointing["camera"].getGeometry():
		    ra.append(ccd[0])
		    ra.append(ccd[2])
		    dec.append(ccd[1])
		    dec.append(ccd[3])
  	        import math
 		dra=math.degrees(math.fabs(max(ra)-min(ra)))
 		ddec=math.degrees(math.fabs(max(dec)-min(dec)))
                f.write("%f %f %16s %16s DATE 1.00 1.00 500 FILE\n" % (dra, ddec, sra, sdec ) ) 
        if self.pointing_format.get()=='CFHT PH':
	    f.write("""]]</CSV></DATA>
</TABLE>
</ASTRO>
""")
	f.close()


class camera:
    """The Field of View of a direct imager"""

    geometry={"MP_CCD":[
        {"ra": 0., "dec": 0., "dra": 0.1052, "ddec": 0.2344 }],
        "MEGACAM_36":[
        {"ra": -0.46, "dec": -0.38, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.35, "dec": -0.38, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.23, "dec": -0.38, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.12, "dec": -0.38, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.00, "dec": -0.38, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.11, "dec": -0.38,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.23, "dec": -0.38,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.35, "dec": -0.38,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.46, "dec": -0.38,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.47, "dec": -0.12, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.35, "dec": -0.12, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.23, "dec": -0.12, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.12, "dec": -0.12, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.00, "dec": -0.12, "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.12, "dec": -0.12,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.23, "dec": -0.12,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.35, "dec": -0.12,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.46, "dec": -0.12,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.47, "dec": 0.12,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.35, "dec": 0.12,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.23, "dec": 0.12,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.12, "dec": 0.12,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.00, "dec": 0.12,   "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.12, "dec": 0.12,   "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.23, "dec": 0.12,   "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.35, "dec": 0.12,   "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.47, "dec": 0.12,   "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.46, "dec": 0.38,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.35, "dec": 0.38,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.23, "dec": 0.38,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": -0.12, "dec": 0.38,  "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.00, "dec": 0.38,   "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.12, "dec": 0.38,   "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.23, "dec": 0.38,   "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.35, "dec": 0.38,   "dra": 0.1052, "ddec": 0.2344 },
        {"ra": 0.47, "dec": 0.38,   "dra": 0.1052, "ddec": 0.2344 }],
                "LFCNS": [
        {"ra": -0.0512, "dec": 0.1045, "dra": .1023, "ddec": 0.2047 },
        {"ra":  0.0512, "dec": 0.1045, "dra": .1023, "ddec": 0.2047 },
        {"ra": -0.0512, "dec": -0.1045, "dra": .1023, "ddec": 0.2047 },
        {"ra":  0.0512, "dec": -0.1045, "dra": .1023, "ddec": 0.2047 },
        {"ra":  0.1536, "dec": 0., "dra": .1023, "ddec": 0.2047 },
        {"ra": -0.1536, "dec": 0., "dra": .1023, "ddec": 0.2047 }],
                "LFCEW": [
        {"dec": -0.0532, "ra": 0.1045, "ddec": .1023, "dra": 0.2047 },
        {"dec":  0.0532, "ra": 0.1045, "ddec": .1023, "dra": 0.2047 },
        {"dec": -0.0532, "ra": -0.1045, "ddec": .1023, "dra": 0.2047 },
        {"dec":  0.0532, "ra": -0.1045, "ddec": .1023, "dra": 0.2047 },
        {"dec":  0.1598, "ra": 0., "ddec": .1023, "dra": 0.2047 },
        {"dec": -0.1598, "ra": 0., "ddec": .1023, "dra": 0.2047 }],
              "MEGACAM_1": [
        {"ra":0,"dec":0,"dra":0.98,"ddec": 0.98}],
	      "MMCAM": [ 
{'ra': -0.162500, 'dec':-0.189444 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.162500, 'dec':-0.141944 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.162500, 'dec':-0.095000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.162500, 'dec':-0.047500 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.162500, 'dec':0.000000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.162500, 'dec':0.047500 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.162500, 'dec':0.095000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.162500, 'dec':0.141944 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.162500, 'dec':0.189444 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.051389, 'dec':-0.189444 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.051389, 'dec':-0.141944 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.051389, 'dec':-0.095000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.051389, 'dec':-0.047500 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.051389, 'dec':0.000000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.051389, 'dec':0.047500 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.051389, 'dec':0.095000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.051389, 'dec':0.141944 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': -0.051389, 'dec':0.189444 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.051389, 'dec':-0.189444 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.051389, 'dec':-0.141944 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.051389, 'dec':-0.095000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.051389, 'dec':-0.047500 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.051389, 'dec':0.000000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.051389, 'dec':0.047500 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.051389, 'dec':0.095000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.051389, 'dec':0.141944 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.051389, 'dec':0.189444 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.162500, 'dec':-0.189444 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.162500, 'dec':-0.141944 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.162500, 'dec':-0.095000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.162500, 'dec':-0.047500 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.162500, 'dec':0.000000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.162500, 'dec':0.047500 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.162500, 'dec':0.095000 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.162500, 'dec':0.141944 , 'dra':0.102222 , 'ddec':0.045333},
{'ra': 0.162500, 'dec':0.189444 , 'dra':0.102222 , 'ddec':0.045333}
],
                "MEGACAM_2":[
        {"ra":0,"dec":-0.252,"dra":0.98,"ddec": 0.478},
        {"ra":0,"dec":+0.235,"dra":0.98,"ddec": 0.478} ],
              "EW-MOSAIC": [
        {"dec":  1.5*0.1479+0.0036, "ra": -0.1479-0.0019, "dra": 2.0*0.1479, "ddec": 0.1479, },
        {"dec":  0.5*0.1479+0.0011, "ra": -0.1479-0.0019, "dra": 2.0*0.1479, "ddec": 0.1479, },
        {"dec": -0.5*0.1479-0.0011, "ra": -0.1479-0.0019, "dra": 2.0*0.1479, "ddec": 0.1479, },
        {"dec": -1.5*0.1479-0.0036, "ra": -0.1479-0.0019, "dra": 2.0*0.1479, "ddec": 0.1479, },
        {"dec":  1.5*0.1479+0.0036, "ra":  0.1479+0.0019, "dra": 2.0*0.1479, "ddec": 0.1479, },
        {"dec":  0.5*0.1479+0.0011, "ra":  0.1479+0.0019, "dra": 2.0*0.1479, "ddec": 0.1479, },
        {"dec": -0.5*0.1479-0.0011, "ra":  0.1479+0.0019, "dra": 2.0*0.1479, "ddec": 0.1479, },
        {"dec": -1.5*0.1479-0.0036, "ra":  0.1479+0.0019, "dra": 2.0*0.1479, "ddec": 0.1479, },
        ],
              "NS-MOSAIC": [
        {"ra":  1.5*0.1479+0.0036, "dec": -0.1479-0.0019, "ddec": 2.0*0.1479, "dra": 0.1479, },
        {"ra":  0.5*0.1479+0.0011, "dec": -0.1479-0.0019, "ddec": 2.0*0.1479, "dra": 0.1479, },
        {"ra": -0.5*0.1479-0.0011, "dec": -0.1479-0.0019, "ddec": 2.0*0.1479, "dra": 0.1479, },
        {"ra": -1.5*0.1479-0.0036, "dec": -0.1479-0.0019, "ddec": 2.0*0.1479, "dra": 0.1479, },
        {"ra":  1.5*0.1479+0.0036, "dec":  0.1479+0.0019, "ddec": 2.0*0.1479, "dra": 0.1479, },
        {"ra":  0.5*0.1479+0.0011, "dec":  0.1479+0.0019, "ddec": 2.0*0.1479, "dra": 0.1479, },
        {"ra": -0.5*0.1479-0.0011, "dec":  0.1479+0.0019, "ddec": 2.0*0.1479, "dra": 0.1479, },
        {"ra": -1.5*0.1479-0.0036, "dec":  0.1479+0.0019, "ddec": 2.0*0.1479, "dra": 0.1479, },
        ],
              "L2": [{"ra":0, "dec": +0.98*0.5, "ddec": 1.0*0.98, "dra": 8.0*0.98},
                     {"ra":0, "dec": -0.98*0.5, "ddec": 1.0*0.98, "dra": 8.0*0.98}]
              }
    

    def __init__(self,camera="MEGACAM_2"):
        if camera=='':
            camera="MEGACAM_2"
        self.camera=camera

    def __str__(self):
        
        return "%s %s" % ( self.ra, self.dec ) 

    def getGeometry(self,ra=None,dec=None):
        """Return an array of rectangles that represent the 'ra,dec' corners of the FOV"""

        import math,ephem
        ccds=[]

        if ra is None:
            ra=self.ra
        if dec is None:
            dec=self.dec
        self.ra=ephem.hours(ra)
        self.dec=ephem.degrees(dec)
        for geo in self.geometry[self.camera]:
            ycen=math.radians(geo["dec"])+dec
            xcen=math.radians(geo["ra"])/math.cos(ycen)+ra
            dy=math.radians(geo["ddec"])
            dx=math.radians(geo["dra"]/math.cos(ycen))
            ccds.append([xcen-dx/2.0,ycen-dy/2.0,xcen+dx/2.0,ycen+dy/2.0])

        return ccds

    
    def separation(self,ra,dec):
        """Compute the separation between self and (ra,dec)"""

        import ephem
        return ephem.separation((self.ra,self.dec),(ra,dec))
    
        
import optparse

parser=optparse.OptionParser()
parser.add_option("-p","--pointings",help="A file containing some pointings")
#parser.add_option("-k","--kbos",help-"File with list of Kuiper belt objects (ra,dec,dra,ddec,ang)")
(opt,files)=parser.parse_args()

        
root=Tk()
### Make the root window resizeable
root.rowconfigure(0,weight=1)
root.columnconfigure(0,weight=1)

### The PLOT frame
pframe=Frame()
pframe.grid(sticky=N+S+E+W)
pframe.rowconfigure(0,weight=1)
pframe.columnconfigure(0,weight=1)

### Make a plot (w) in the plotFrame
## with scroll bars
w=plot(pframe)
sx=Scrollbar(pframe,orient=HORIZONTAL,command=w.xview)
sy=Scrollbar(pframe,orient=VERTICAL,command=w.yview)
w.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
sx.grid(row=1,column=0,sticky=E+W)
sy.grid(row=0,column=1,sticky=N+S)

### Get the mouse to do intersting stuff
w.bind('<Key-g>',w.helio_grid)
w.bind('<Motion>',w.pos_update)
w.bind('<Double-Button-1>',w.create_pointing)
w.bind('<Key-Delete>',w.delete_pointing)
w.bind('<Key-BackSpace>',w.delete_pointing)
w.bind('<B1-Motion>',w.move_pointing)
w.bind('<Control-equal>',w.zoom_in)
w.bind('<Control-minus>',w.zoom_out)
w.bind('<Key-c>',w.center)
w.bind('<Control-Button-1>',w.center)
w.grid(row=0,column=0,sticky=N+S+E+W)

### The infomration Panel
infoPanel=Frame(root)
### Coordinates box
coordsBox=Frame(infoPanel)
Label(coordsBox,text="Heliocentric:").grid(row=0,column=0,sticky=E)
Label(coordsBox,textvariable=w.heliocentric).grid(row=0,column=1,sticky=W)
Label(coordsBox,text="Equatorial:").grid(row=1,column=0,sticky=E)
Label(coordsBox,textvariable=w.equatorial).grid(row=1,column=1,sticky=W)
Label(coordsBox,text="Solar Elong.:").grid(row=3,column=0,sticky=E)
Label(coordsBox,textvariable=w.elongation).grid(row=3,column=1,sticky=W)


Entry(coordsBox,textvariable=w.date).grid(row=6,column=1,sticky=W)
Label(coordsBox,text="Date: ").grid(row=6,column=0,sticky=E)
Button(coordsBox,text="Update ",command=w.reset).grid(row=6,column=2,sticky=W)

Label(coordsBox,text="Pointing:").grid(row=8,column=0,sticky=W)
Entry(coordsBox,textvariable=w.plabel).grid(row=9,column=1,sticky=W)
Label(coordsBox,text="Label:").grid(row=9,column=0,sticky=E)
Button(coordsBox,text="Update Label",command=w.set_pointing_label).grid(row=9,column=2,sticky=W)


Label(coordsBox,text="Objects").grid(row=12,column=0,sticky=W)
Entry(coordsBox,textvariable=w.SearchVar).grid(row=13,column=1,sticky=W)
Label(coordsBox,text="Search:").grid(row=13,column=0,sticky=E)
Button(coordsBox,text="GoTo: ",command=w.relocate).grid(row=13,column=2,sticky=W)

Entry(coordsBox,textvariable=w.FilterVar).grid(row=14,column=1,sticky=W)
Button(coordsBox,text="Filter",command=w.reset).grid(row=14,column=2,sticky=W)


### put a list of the currently visible sources
ObjBox=Frame(infoPanel)
ObjBox.grid(row=1,column=0)
w.objList=Listbox(ObjBox,height=15)
w.objList.grid(row=1,column=0)
w.objList.bind('<Button-1>',w.updateObj)

ObjInfoBox=Frame(infoPanel)
ObjInfoBox.grid(row=2,column=0)
w.objInfo=Label(ObjInfoBox,justify=LEFT,font=("Helvetica", 16),textvariable=w.ObjInfo)
w.objInfo.grid(row=1,column=0)


coordsBox.grid(row=0,column=0,sticky=NE)

### Pack the major frame bits
pframe.grid(row=0,column=0)
infoPanel.grid(row=0,column=1,sticky=NE)

### ROOT menu bar
menubar=Menu(root)

file_menu = Menu(menubar,tearoff=0)
file_menu.add_command(label="Save as .eps", command=w.eps)
menubar.add_cascade(label="File", menu=file_menu)

### MENU To add sources
source_menu= Menu(menubar,tearoff=0)
source_menu.add_command(label="Select ABG File Directory",command=load_abgfiles)
source_menu.add_command(label="Load ephem.db File",command=load_edbfile)
source_menu.add_checkbutton(label='Show Labels',variable=w.show_labels,onvalue=1,command=w.reset)
source_menu.add_checkbutton(label='Show Ellipses',variable=w.show_ellipse,onvalue=1,command=w.reset)
menubar.add_cascade(label="Objects", menu=source_menu)

pointing_menu=Menu(menubar,tearoff=0)
pointing_menu.add_command(label="Load pointings",command=w.load_pointings)

pointFormat=Menu(pointing_menu,tearoff=0)
pointFormat.add_checkbutton(label='CFHT PH', variable=w.pointing_format,onvalue='CFHT PH')
pointFormat.add_checkbutton(label='Palomar', variable=w.pointing_format,onvalue='Palomar')
pointFormat.add_checkbutton(label='KPNO/CTIO', variable=w.pointing_format,onvalue='KPNO/CTIO')
pointFormat.add_checkbutton(label='SSim', variable=w.pointing_format,onvalue='SSim')
pointing_menu.add_cascade(label='Save Format',menu=pointFormat)

pointing_menu.add_command(label="Save pointings",command=w.save_pointings)
pointing_menu.add_command(label="Clear pointings",command=w.clear_pointings)
pointing_menu.add_command(label="Query pointings",command=w.get_pointings)

cameramenu=Menu(pointing_menu,tearoff=0)
for name in camera.geometry:
    cameramenu.add_checkbutton(label=name,variable=w.camera,onvalue=name)

pointing_menu.add_cascade(label="Geometry",menu=cameramenu)


menubar.add_cascade(label="Pointings", menu=pointing_menu)


### Zoom Menu
viewmenu=Menu(root)
viewmenu.add_command(label="Zoom In",command=w.zoom_in)
viewmenu.add_command(label="Zoom Out",command=w.zoom_out)
viewmenu.add_command(label="Reset Plot",command=w.reset)
menubar.add_cascade(label="View", menu=viewmenu)



### Stick on the root menubar
root.config(menu=menubar)

import sys

kbos={}
objInfoDict={}

def doplot(depricated=None):
    import Tkinter,math,ephem
    w.delete(Tkinter.ALL)
    w.coord_grid()
    w.objList.delete(0,END)
    do_objs(kbos)
    do_objs(mpc_objs)

def do_objs(kbos):
    """Draw the actual plot"""

    import orbfit, ephem, math
    import re
    re_string=w.FilterVar.get()
    vlist=[]
    for name in kbos:
        if not re.search(re_string,name):
            continue
        vlist.append(name)
        if type(kbos[name])==type(ephem.EllipticalBody()):
	    kbos[name].compute(w.date.get())
	    ra=kbos[name].ra
	    dec=kbos[name].dec
	    a=math.radians(10.0/3600.0)
	    b=a
	    ang=0.0
	    color='blue'
            yoffset=+10
	    xoffset=+10
        else:
            yoffset=-10
            xoffset=-10
            file=kbos[name]
	    jdate=ephem.julian_date(w.date.get())
	    obs=568
 	    try:
	        position=orbfit.predict(file,jdate,obs)
	    except:
		continue
	    ra=math.radians(position[0])
	    dec=math.radians(position[1])
	    a=math.radians(position[2]/3600.0)
	    b=math.radians(position[3]/3600.0)
	    ang=math.radians(position[4])
	    if ( a> math.radians(1.0) ):
	        color='green'
            else:
	        color='black'
	if w.show_ellipse.get()==1 :
            if ( a < math.radians(5.0) ): 
	        w.create_ellipse(ra,dec,a,b,ang)
        if ( a < math.radians(1.0) ): 
            w.create_point(ra,dec,size=2,color=color)
	if w.show_labels.get()==1:
	    w.label(ra,dec,name,offset=[xoffset,yoffset])
    vlist.sort()
    for v in vlist:
        w.objList.insert(END,v)
    w.plot_pointings()

### read in pointings, from a command line file...

w.newPlot()
root.mainloop()
