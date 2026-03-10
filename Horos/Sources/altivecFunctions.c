/*=========================================================================
  Program:   OsiriX

  Copyright (c) OsiriX Team
  All rights reserved.
  Distributed under GNU - LGPL
  
  See http://www.osirix-viewer.com/copyright.html for details.

     This software is distributed WITHOUT ANY WARRANTY; without even
     the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
     PURPOSE.
 ---------------------------------------------------------------------------
 
 This file is part of the Horos Project.
 
 Current contributors to the project include Alex Bettarini and Danny Weissman.
 
 Horos is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation,  version 3 of the License.
 
 Horos is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 
 You should have received a copy of the GNU General Public License
 along with Horos.  If not, see <http://www.gnu.org/licenses/>.

 

 
 ---------------------------------------------------------------------------
 
 This file is part of the Horos Project.
 
 Current contributors to the project include Alex Bettarini and Danny Weissman.
 
 Horos is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation,  version 3 of the License.
 
 Horos is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 
 You should have received a copy of the GNU General Public License
 along with Horos.  If not, see <http://www.gnu.org/licenses/>.

=========================================================================*/

#include "altivecFunctions.h"

void vmax8ARM( vUInt8 *a, vUInt8 *b, vUInt8 *r, long size)
{
long i = size/4;

while(i-- > 0)
{
*r++ = vreinterpretq_s32_u8(vmaxq_u8(vreinterpretq_u8_s32( *a++ ), vreinterpretq_u8_s32( *b++ )));
}
}

void vmin8ARM( vUInt8 *a, vUInt8 *b, vUInt8 *r, long size)
{
long i = size/4;

while(i-- > 0)
{
*r++ = vreinterpretq_s32_u8(vminq_u8(vreinterpretq_u8_s32( *a++ ), vreinterpretq_u8_s32( *b++ )));
}
}

void vmultiplyNoAltivec( float *a,  float *b,  float *r, long size)
{
long i = size;

while(i-- > 0)
{
*r++ = *a++ * *b++;
}
}

void vsubtractNoAltivec( float *a,  float *b,  float *r, long size)
{
long i = size;

while(i-- > 0)
{
*r++ = *a++ - *b++;
}
}

void vsubtractNoAltivecAbs( float *a,  float *b,  float *r, long size)
{
long i = size;

while(i-- > 0)
{
*r++ = fabsf(*a++ - *b++);
}
}

void vmaxNoAltivec(float *a, float *b, float *r, long size)
{
long i = size;

while(i-- > 0)
{
if( *a > *b) { *r++ = *a++; b++; }
else { *r++ = *b++; a++; }
}
}

void vminNoAltivec( float *a,  float *b,  float *r, long size)
{
long i = size;

while(i-- > 0)
{
if( *a < *b) { *r++ = *a++; b++; }
else { *r++ = *b++; a++; }
}
}
