#include "procmega.h"

float **getpixmem(int ysize, int xsize) {
  float **m;
  int i;
  /* allocate pointers to rows */
  m=(float **) malloc(ysize*sizeof(float *));
  if (!m) {
    fprintf(stdout, "Memory allocation error 1 in getpixmem\n");
    exit(-1);
  }
  /* allocate rows and set pointers to them */
  for (i=0; i<ysize; i++) {
    m[i] = (float *) malloc(xsize*sizeof(float));
    if (!m[i]){ 
      fprintf(stdout, "Memory allocation error 2 in getpixmem\n");
      exit(-1);
    }
  }
  return m;
  /* do it this way round - block[y][x] - because this is what fits likes */
}

int get_imagedata_over(float **dataleft, float **dataright, float **biasleft, 
		  float **biasright, int *BL, int *BR, int *DL, int *DR, 
		  char *infilechip) {

  fitsfile *infptr;
  int fitserr=0;
  int bitpix;
  int naxis=0;          /* dimensions of the data */
  long naxes[2]={1,1};  /* size of data buffer - will be updated below */ 
  long fpixel[2]={1,1}, lpixel[2]={1,1}; /* specify regions of image */ 
  long inc[2]={1,1}; /* read every pixel */
  int anynul;
  float nulval = -100000;
  float *array, *datpt, *datpt2;
  int nx, ny;
  long nelements;
  int ii,jj, i, j;

  /* allocate array big enough to hold incoming data */
  ny=DR[3]-DR[2]+1;
  nx=DR[1]-DR[0]+1;
  array = (float *) malloc ((nx*ny)*sizeof(float));

  /* open file */
  fitserr =0;
  fprintf(stdout,"Opening image %s\n", infilechip );
  fits_open_file(&infptr, infilechip, READONLY, &fitserr);
  /* any errors? */
  if (fitserr!=0) {
    fprintf(stdout, "Error opening image %s\n", infilechip);
    fits_report_error(stdout, fitserr);
  }
  /* get image info */
  fits_get_img_param(infptr, 2, &bitpix, &naxis, naxes, &fitserr);
  if ((naxis!=2) || (naxes[0]!=2112) || (naxes[1]!=4644)) { 
    fprintf(stdout, "Found axis length %d\n", naxis);
    fprintf(stdout, "Found naxes[0] %d :  naxes[1] %d\n", naxes[0], naxes[1]);
    fprintf(stdout, "Hmm.. these dimensions are not what I'm expecting\n");
  }
  
  /* naxes saves total size of image, but I'll use what I think bias 
     and image sizes are anyway .. though these could be read from image keys */

  /* read bias left side */
  fpixel[0] = BL[0];
  fpixel[1] = BL[2];
  lpixel[0] = BL[1];
  lpixel[1] = BL[3];
  fprintf(stdout, "bias left coords %d %d %d %d\n", fpixel[0], fpixel[1], 
      lpixel[0], lpixel[1]); 
  fits_read_subset(infptr, TFLOAT, fpixel, lpixel, inc, &nulval, array,
		   &anynul, &fitserr);
  /* have to add one to ny/nx, again, because must start counting at 1 */ 
  ny = BL[3] - BL[2] + 1;
  nx = BL[1] - BL[0] + 1;
  datpt = array;
  i=0;
  for (jj=0; jj<ny; jj++) {
    datpt2 = &biasleft[jj][0];
    for (ii=0; ii<nx; ii++) {
      *datpt2 = *datpt;
      datpt++;
      datpt2++;
    }
  }
  
  /* read data right side */
  fpixel[0]=DR[0];
  fpixel[1]=DR[2];
  lpixel[0]=DR[1];
  lpixel[1]=DR[3];
  ny = DR[3] - DR[2] + 1;
  nx = DR[1] - DR[0] + 1;
  nelements = nx*ny;
  fprintf(stdout, "data right coords %d %d %d %d, nx %d ny %d nelements %d\n", 
	  fpixel[0], fpixel[1],
	  lpixel[0], lpixel[1], nx, ny, nelements);
  /*  fits_read_pix(infptr, TFLOAT, fpixel, nelements, &nulval, array, &anynul, &fitserr); */
  fits_read_subset(infptr, TFLOAT, fpixel, lpixel, inc, &nulval, array,
      &anynul, &fitserr); 
  datpt = array;
  for (jj=0; jj<ny; jj++) {
    datpt2 = &dataright[jj][0];
    for (ii=0; ii<nx; ii++) {
      *datpt2 = *datpt;
      datpt++;
      datpt2++;
    }
  }

  /* read data left side*/
  fpixel[0]=DL[0];
  fpixel[1]=DL[2];
  lpixel[0]=DL[1];
  lpixel[1]=DL[3];
  fprintf(stdout, "data left coords %d %d %d %d\n", fpixel[0], fpixel[1],
	  lpixel[0], lpixel[1]); 
  fits_read_subset(infptr, TFLOAT, fpixel, lpixel, inc, &nulval, array,
		   &anynul, &fitserr);
  ny = DL[3] - DL[2] + 1;
  nx = DL[1] - DL[0] + 1;
  datpt = array;
  for (jj=0; jj<ny; jj++) {
    datpt2 = &dataleft[jj][0];
    for (ii=0; ii<nx; ii++) {
      *datpt2 = *datpt;
      datpt++;
      datpt2++;
    }
  }


  /* read bias right side */
  fpixel[0]=BR[0];
  fpixel[1]=BR[2];
  lpixel[0]=BR[1];
  lpixel[1]=BR[3];
  fprintf(stdout, "bias right coords %d %d %d %d\n", fpixel[0], fpixel[1], 
	lpixel[0], lpixel[1]); 
  fits_read_subset(infptr, TFLOAT, fpixel, lpixel, inc, &nulval, array,
		   &anynul, &fitserr);
  ny = BR[3] - BR[2] + 1;
  nx = BR[1] - BR[0] + 1;
  datpt = array;
  for (jj=0; jj<ny; jj++) {
    datpt2 = &biasright[jj][0];
    for (ii=0; ii<nx; ii++) {
      *datpt2 = *datpt;
      datpt++;
      datpt2++;
    }
  }
  
  /* done getting data, can close the file */
  fits_close_file(infptr, &fitserr);
  /* and free array memory */
  free(array);

  /* check for any errors */
  if (fitserr!=0) {
    fits_report_error(stdout, fitserr);
  }  
  
  return(fitserr);
}


int get_fullimage(float **data, int *DA, char *infilename) {

  /* data is data array returned, DA is size of image array, infilename is name of image */

  fitsfile *infptr;
  int fitserr=0;
  int anynul;
  float nulval = -100000;
  float *array, *datpt, *datpt2;
  int ii, jj;
  int nx, ny;
  int bitpix;
  int naxis=0;          /* dimensions of the data */
  long naxes[2]={1,1};  /* size of data buffer - will be updated below */ 
  long fpixel[2]={1,1}; /* specify regions of image */ 
  long nelements;
  
  fpixel[0] = DA[0];
  fpixel[1] = DA[2];
  nelements = (DA[1]-DA[0]+1)*(DA[3]-DA[2]+1);

  /* allocate array to hold image */
  array = (float * ) malloc (nelements*sizeof(float));
  
  /* open file */
  fprintf(stdout, "Opening trimmed image %s\n", infilename);
  fits_open_file(&infptr, infilename, READONLY, &fitserr);
  /* any errors ? */
  if (fitserr!=0) {
    fprintf(stdout, "Error opening image %s\n", infilename);
    fits_report_error(stdout, fitserr);
  }
  
  /* get image info */
  fits_get_img_param(infptr, 2, &bitpix, &naxis, naxes, &fitserr);
  if ((naxis!=2) || (naxes[0]!=DA[1]) || (naxes[1]!=DA[3])) { 
    fprintf(stdout, "Found axis length %d\n", naxis);
    fprintf(stdout, "Found naxes[0] %d  naxes[1] %d\n", naxes[0], naxes[1]);
    fprintf(stdout, "Hmm.. these dimensions are not what I'm expecting\n");
  }

  /* read image data */
  fits_read_pix(infptr, TFLOAT, fpixel, nelements, &nulval, array, 
		&anynul, &fitserr);
  nx = DA[1] - DA[0] + 1;
  ny = DA[3] - DA[2] + 1;
  datpt2 = array;
  for (jj=0; jj<ny; jj++) {
    datpt = &data[jj][0];
    for (ii=0; ii<nx; ii++) {
      *datpt = *datpt2;
      datpt++ ;
      datpt2++ ;
    }
  }
  fprintf(stdout, "Read image %s with size %d %d\n", infilename, nx, ny);
  free(array);
  fits_close_file(infptr, &fitserr);
  if (fitserr!=0)
    fits_report_error(stdout, fitserr);
  return(fitserr);
}


int write_image(float **data, int *DA, char *infilechip, int nchip, int flipchips, float avebiasleft, float avebiasright) {
  
  fitsfile *infptr, *outfptr;
  int fitserr=0;
  int ofitserr=0;
  int nkeys, morekeys; /* nkeys is number of keywords - minus END keyword */
  int bitpix = USHORT_IMG; /* set to SHORT_IMG type, 16 bit */
  int naxis = 2;
  long naxes[2] = {1,1};
  char outfilename[80];
  char keyname[9];
  char keyvalue[FLEN_VALUE]; /* key word value */
  char keycomment[FLEN_COMMENT];
  char keycard[FLEN_CARD]; /* entire key card, includes name/value/comment */
  int ii, jj;
  long fpixel[2]={1,1};
  long nelements;
  int nx, ny;
  float *array, *datapt, *datapt2;
  float crpix1, crpix2;
  float cd1, cd2;
  int flag=0;
  int flipflag=0;
  
  /* this subroutine will write each chip independently to separate file */
  /* output image name will be based on object or field name in fits keyword in infile */
  /* this is intended for first run use, when separating mosaic images */

  nx = DA[1] - DA[0] + 1;
  ny = DA[3] - DA[2] + 1;
  nelements = nx*ny;
  fprintf(stdout, "nx %d ny %d nelements %d\n", nx, ny, nelements);

  /* open input file to get header info */
  fits_open_file(&infptr, infilechip, READONLY, &fitserr);
  /* any errors? */
  if (fitserr!=0) {
    fprintf(stdout, "Error opening image %s\n", infilechip);
    fits_report_error(stdout, fitserr);
  }  
  
  fits_get_hdrspace(infptr, &nkeys, &morekeys, &fitserr); 

  /* set up output file name */
  strcpy(keyname, "FILENAME"); /* could also use OBJECT & a number */
  fits_read_key(infptr, TSTRING, keyname, keyvalue, keycomment, &fitserr); 
  sprintf(outfilename, "%s_%.2d.fits", keyvalue, nchip); 
  /* sprintf(outfilename, "%s_%.2d.fits", infilechip, nchip); */
  fprintf(stdout, "Writing to image filename %s\n", outfilename);
  
  /* create output file */
  fits_create_file(&outfptr, outfilename, &ofitserr);
  if (ofitserr!=0) {
    fprintf(stdout, "Error creating image %s\n", outfilename);
    fits_report_error(stdout, ofitserr);
    return(-1);
  }
  
  /* copy header information */
  bitpix=32; /* 32 for floats, 16 for shorts */
  fits_create_img(outfptr, bitpix, naxis, naxes, &ofitserr);  
  /*  fits_copy_header(infptr, outfptr, &ofitserr); */
  for (ii=1; ii<=nkeys; ii++) {
    fits_read_record(infptr, ii, keycard, &fitserr);
    if (fits_get_keyclass(keycard) > TYP_CMPRS_KEY)
      fits_write_record(outfptr, keycard, &ofitserr);
  }
  
  /* then update naxis naxes in output image for what I want */
  strcpy(keyname, "BITPIX");
  fits_update_key(outfptr, TINT, keyname, &bitpix, NULL, &ofitserr);
  strcpy(keyname, "NAXIS");
  fits_update_key(outfptr, TINT, keyname, &naxis, NULL, &ofitserr);
  strcpy(keyname, "NAXIS1");
  fits_update_key(outfptr, TLONG, keyname, &nx, NULL, &ofitserr);
  strcpy(keyname, "NAXIS2");
  fits_update_key(outfptr, TLONG, keyname, &ny, NULL, &ofitserr);
  /* and add CHIPID keyword */
  strcpy(keyname, "CHIPID");
  strcpy(keycomment, "Chipid -  starts at 0");
  fits_write_key(outfptr, TINT, keyname, &nchip, keycomment, &ofitserr);

  if (ofitserr!=0) {
    fprintf(stdout, "Error in writing output image %s\n", outfilename);
    fits_report_error(stdout, ofitserr);
  }

  /* write some comments about what done to data now */
  fits_write_history(outfptr, "Processed with procmega", &ofitserr);
  fits_write_history(outfptr, "Overscan subtracted from each side and trimmed", &ofitserr);
  sprintf(keycomment, "Left overscan value %f", avebiasleft);
  fits_write_history(outfptr, keycomment, &ofitserr);
  sprintf(keycomment, "Right overscan value %f", avebiasright);
  fits_write_history(outfptr, keycomment, &ofitserr);
  /* change CRPIX values to account for trim section removal */
  strcpy(keyname, "CRPIX1");
  fits_read_key(infptr, TFLOAT, keyname, &crpix1, keycomment, &fitserr); 
  strcpy(keyname, "CRPIX2");
  fits_read_key(infptr, TFLOAT, keyname, &crpix2, keycomment, &fitserr); 
  /* crpix1 = crpix1 + DL[0] - 1; */ 
  crpix1 = crpix1 + 32;
  /* only changes crpix in X because trim only important to 1,1 in X */
  strcpy(keyname, "CRPIX1");
  fits_update_key(outfptr, TFLOAT, keyname, &crpix1, NULL, &ofitserr);
  strcpy(keyname, "TRIM");
  flag=1;
  fits_write_key(outfptr, TINT, keyname, &flag, NULL, &ofitserr);
  strcpy(keyname, "OVERSCAN");
  flag=1;
  fits_write_key(outfptr, TINT, keyname, &flag, NULL, &ofitserr);
  if (flipchips) {
    if (nchip<=HALFMEGA) {
      /* need to change crpix if changed orientation */
      crpix1 = DA[1] - crpix1;
      crpix2 = DA[3] - crpix2;
      strcpy(keyname, "CRPIX1");
      fits_update_key(outfptr, TFLOAT, keyname, &crpix1, NULL, &ofitserr);
      strcpy(keyname, "CRPIX2");
      fits_update_key(outfptr, TFLOAT, keyname, &crpix2, NULL, &ofitserr);
      /* also need to swap CD1_1 and CD2_2 to give flip */
      strcpy(keyname, "CD1_1");
      fits_read_key(infptr, TFLOAT, keyname, &cd1, keycomment, &fitserr);
      strcpy(keyname, "CD2_2");
      fits_read_key(infptr, TFLOAT, keyname, &cd2, keycomment, &fitserr);
      strcpy(keyname, "CD1_1");
      fits_update_key(outfptr, TFLOAT, keyname, &cd2, NULL, &ofitserr);
      strcpy(keyname, "CD2_2");
      fits_update_key(outfptr, TFLOAT, keyname, &cd1, NULL, &ofitserr);
    }
    strcpy(keyname, "FLIPPED");
    flipflag = 1;
    fits_write_key(outfptr, TINT, keyname, &flipflag, NULL, &ofitserr);
    fits_write_history(outfptr, "Chips 1-18 flipped N/S and E/W", &fitserr);
  }
  
  
  /* write in data */
  /* copy data to array for output through fitsio */
  array = (float *) malloc(nx*ny*sizeof(float));
  datapt = array;
  for (jj=0; jj<ny; jj++) {
    datapt2 = &data[jj][0];
    for (ii=0; ii<nx; ii++) {
      *datapt = *datapt2;
      /*      if (ii<nx/2) *datapt = 0;
	      else *datapt=1;   */
      datapt++;
      datapt2++;
    }
  }
  
  fits_write_pix(outfptr, TFLOAT, fpixel, nelements, array, &ofitserr);

  free(array);
  /* close files */
  fits_close_file(infptr, &fitserr);
  if (fitserr!=0) {
    fprintf(stdout, "Error in writing image, with copying image headers\n");
    fits_report_error(stdout, fitserr);
  }
  fits_close_file(outfptr, &ofitserr);
  if (ofitserr!=0) {
    fprintf(stdout, "Error in writing output image %s\n", outfilename);
    fits_report_error(stdout, ofitserr);
  }

  return(ofitserr);
  
}


int write_procimage(float **data, int *DA, char *infilename, int usebias, int useflat, char *biasname, char *flatname) {
  
  fitsfile *fptr;
  int fitserr=0;
  int nkeys, morekeys; /* nkeys is number of keywords - minus END keyword */
  int naxis = 2;
  long naxes[2] = {1,1};
  char outfilename[80];
  char keyname[9];
  char keyvalue[FLEN_VALUE]; /* key word value */
  char keycomment[FLEN_COMMENT];
  char keycard[FLEN_CARD]; /* entire key card, includes name/value/comment */
  int ii, jj;
  long fpixel[2]={1,1};
  long nelements;
  int nx, ny;
  float *array, *datapt, *datapt2;
  float BADTHRESHOLD=-10000;
  float BADPIX=0;
  int flag=0;

  /* this subroutine just writes processed data back to image */
  /* note - overwrites previous image, in order to save disk space */
  nx = DA[1] - DA[0] + 1;
  ny = DA[3] - DA[2] + 1;
  nelements = nx*ny;
  fprintf(stdout, "nx %d ny %d nelements %d\n", nx, ny, nelements);

  /* open input file to get header info */
  fits_open_file(&fptr, infilename, READWRITE, &fitserr);
  /* any errors? */
  if (fitserr!=0) {
    fprintf(stdout, "Error opening image %s\n", infilename);
    fits_report_error(stdout, fitserr);
  }  

  fprintf(stdout, "Re-Writing to image filename %s\n", infilename);
  
  /* write some comments about what done to data now */
  fits_write_history(fptr, "Processed with procmega", &fitserr);
  if (usebias) {
    flag=1;
    strcpy(keyname, "BIAS");
    fits_write_key(fptr, TINT, keyname, &flag, NULL, &fitserr);
    sprintf(keycomment, "Bias %s subtracted from image", biasname);
    fits_write_history(fptr, keycomment, &fitserr);
    flag=0;
  }
  if (useflat) {
    flag=1;
    strcpy(keyname, "FLAT");
    fits_write_key(fptr, TINT, keyname, &flag, NULL, &fitserr);
    sprintf(keycomment, "Flatfield %s divided into image", flatname);
    fits_write_history(fptr, keycomment, &fitserr);
  }

  /* write in data */
  /* copy data to array for output through fitsio */
  array = (float *) malloc(nx*ny*sizeof(float));
  datapt = array;
  for (jj=0; jj<ny; jj++) {
    datapt2 = &data[jj][0];
    for (ii=0; ii<nx; ii++) {
      *datapt = *datapt2;
      if (*datapt < BADTHRESHOLD) 
	*datapt = BADPIX;
      datapt++;
      datapt2++;
    }
  }
  
  fits_write_pix(fptr, TFLOAT, fpixel, nelements, array, &fitserr);
  
  free(array);
  /* close files */
  fits_close_file(fptr, &fitserr);
  if (fitserr!=0) {
    fits_report_error(stdout, fitserr);
  }
  return(fitserr);
  
}


int write_ushortimage(float **data, int *DA, char *infilename) {
  
  fitsfile *infptr, *outfptr;
  int fitserr=0;
  int ofitserr=0;
  int nkeys, morekeys; /* nkeys is number of keywords - minus END keyword */
  int bitpix = USHORT_IMG; /* set to SHORT_IMG type, 16 bit */
  int naxis = 2;
  long naxes[2] = {1,1};
  char outfilename[80];
  char command[100];
  char keyname[9];
  char keyvalue[FLEN_VALUE]; /* key word value */
  char keycomment[FLEN_COMMENT];
  char keycard[FLEN_CARD]; /* entire key card, includes name/value/comment */
  int ii, jj;
  long fpixel[2]={1,1};
  long nelements;
  int nx, ny;
  float *array, *datapt, *datapt2;
  float crpix1, crpix2;
  float cd1, cd2;
  int flag=0;
  int flipflag=0;
  
  float MINTHRESHOLD = 0.0;
  float MAXTHRESHOLD = 65535.0;
  float bscale = 1.0, bzero = 32768.0;
  
  /* this subroutine will write each chip independently to separate file */
  /* output image name will be based on object or field name in fits keyword in infile */
  /* this is intended for first run use, when separating mosaic images */

  nx = DA[1] - DA[0] + 1;
  ny = DA[3] - DA[2] + 1;
  nelements = nx*ny;
  fprintf(stdout, "nx %d ny %d nelements %d\n", nx, ny, nelements);

  /* open input file to get header info */
  fits_open_file(&infptr, infilename, READONLY, &fitserr);
  /* any errors? */
  if (fitserr!=0) {
    fprintf(stdout, "Error opening image %s\n", infilename);
    fits_report_error(stdout, fitserr);
  }  
  
  fits_get_hdrspace(infptr, &nkeys, &morekeys, &fitserr); 

  /* set up output file name */
  strcpy(keyname, "FILENAME"); /* could also use OBJECT & a number */
  fits_read_key(infptr, TSTRING, keyname, keyvalue, keycomment, &fitserr); 
  sprintf(outfilename, "procmega_tmp_file_123.fits"); 
  fprintf(stdout, "Writing to image filename %s\n", outfilename);
  
  /* create output file */
  fits_create_file(&outfptr, outfilename, &ofitserr);
  if (ofitserr!=0) {
    fprintf(stdout, "Error creating image %s\n", outfilename);
    fits_report_error(stdout, ofitserr);
    return(-1);
  }
  
  /* copy header information */
  bitpix=USHORT_IMG;
  fits_create_img(outfptr, bitpix, naxis, naxes, &ofitserr);  
  /*  fits_copy_header(infptr, outfptr, &ofitserr); */
  for (ii=1; ii<=nkeys; ii++) {
    fits_read_record(infptr, ii, keycard, &fitserr);
    if (fits_get_keyclass(keycard) > TYP_CMPRS_KEY)
      fits_write_record(outfptr, keycard, &ofitserr);
  }
  
  /* then update naxis naxes in output image for what I want */
  /*  strcpy(keyname, "BITPIX"); */
  /*  fits_update_key(outfptr, TINT, keyname, &bitpix, NULL, &ofitserr); */
  strcpy(keyname, "NAXIS");
  fits_update_key(outfptr, TINT, keyname, &naxis, NULL, &ofitserr);
  strcpy(keyname, "NAXIS1");
  fits_update_key(outfptr, TLONG, keyname, &nx, NULL, &ofitserr);
  strcpy(keyname, "NAXIS2");
  fits_update_key(outfptr, TLONG, keyname, &ny, NULL, &ofitserr);

  /* write some comments about what done to data now */
  fits_write_history(outfptr, "Processed with procmega", &ofitserr);
  strcpy(keyname, "BSCALE");
  fits_update_key(outfptr, TFLOAT, keyname, &bscale, NULL, &ofitserr);
  strcpy(keyname, "BZERO");
  fits_update_key(outfptr, TFLOAT, keyname, &bzero, NULL, &ofitserr);
  sprintf(keycomment, "Pixel type changed from REAL to USHORT");
  fits_write_history(outfptr, keycomment, &ofitserr);

  if (ofitserr!=0) {
    fprintf(stdout, "Error in writing output image %s\n", outfilename);
    fits_report_error(stdout, ofitserr);
  }

  /* write in data */
  /* copy data to array for output through fitsio */
  array = (float *) malloc(nx*ny*sizeof(float));
  datapt = array;
  for (jj=0; jj<ny; jj++) {
    datapt2 = &data[jj][0];
    for (ii=0; ii<nx; ii++) {
      *datapt = *datapt2;
      if (*datapt < MINTHRESHOLD) 
	*datapt = MINTHRESHOLD;
      if (*datapt > MAXTHRESHOLD) 
	*datapt = MAXTHRESHOLD;
      datapt++;
      datapt2++;
    }
  }

  fits_write_pix(outfptr, TFLOAT, fpixel, nelements, array, &ofitserr);

  free(array);
  /* close files */
  fits_close_file(infptr, &fitserr);
  if (fitserr!=0) {
    fprintf(stdout, "Error in writing image, with copying image headers\n");
    fits_report_error(stdout, fitserr);
  }
  fits_close_file(outfptr, &ofitserr);
  if (ofitserr!=0) {
    fprintf(stdout, "Error in writing output image %s\n", outfilename);
    fits_report_error(stdout, ofitserr);
  }

  fprintf(stdout, "Moving temporary file %s to %s\n", outfilename, infilename);
  sprintf(command, "mv -f %s %s", outfilename, infilename);
  system(command);

  return(ofitserr);
  
}
