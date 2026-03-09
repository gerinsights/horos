/*=========================================================================
 This file is part of the Horos Project (www.horosproject.org)
 
 Horos is free software: you can redistribute it and/or modify
 it under the terms of the GNU Lesser General Public License as published by
 the Free Software Foundation,  version 3 of the License.
 
 The Horos Project was based originally upon the OsiriX Project which at the time of
 the code fork was licensed as a LGPL project.  However, not all of the the source-code
 was properly documented and file headers were not all updated with the appropriate
 license terms. The Horos Project, originally was licensed under the  GNU GPL license.
 However, contributors to the software since that time have agreed to modify the license
 to the GNU LGPL in order to be conform to the changes previously made to the
 OsiriX Project.
 
 Horos is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY EXPRESS OR IMPLIED, INCLUDING ANY WARRANTY OF
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE OR USE.  See the
 GNU Lesser General Public License for more details.
 
 You should have received a copy of the GNU Lesser General Public License
 along with Horos.  If not, see http://www.gnu.org/licenses/lgpl.html
 
 Prior versions of this file were published by the OsiriX team pursuant to
 the below notice and licensing protocol.
 ============================================================================
 Program:   OsiriX
  Copyright (c) OsiriX Team
  All rights reserved.
  Distributed under GNU - LGPL
  
  See http://www.osirix-viewer.com/copyright.html for details.
     This software is distributed WITHOUT ANY WARRANTY; without even
     the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
     PURPOSE.
 ============================================================================*/

#import "DDKeychain.h"
#import "DICOMTLS.h"
#include <stdio.h>

static NSMutableDictionary *lockedFiles = nil;
static NSRecursiveLock *lockFile = nil;

@implementation DDKeychain

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#pragma mark Server:
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/**
 * Retrieves the password stored in the keychain for the HTTP server.
**/
+ (NSString *)passwordForHTTPServer
{
	NSDictionary *query = @{
		(__bridge id)kSecClass:       (__bridge id)kSecClassGenericPassword,
		(__bridge id)kSecAttrService: @"OsiriX HTTP Server",
		(__bridge id)kSecAttrAccount: @"OsiriX",
		(__bridge id)kSecReturnData:  @YES,
		(__bridge id)kSecMatchLimit:  (__bridge id)kSecMatchLimitOne
	};
	CFDataRef result = NULL;
	OSStatus status = SecItemCopyMatching((__bridge CFDictionaryRef)query, (CFTypeRef *)&result);
	if (status == errSecSuccess && result) {
		NSString *password = [[[NSString alloc] initWithData:(__bridge NSData *)result
		                                            encoding:NSUTF8StringEncoding] autorelease];
		CFRelease(result);
		return password;
	}
	return nil;
}


/**
 * This method sets the password for the HTTP server.
**/
+ (BOOL)setPasswordForHTTPServer:(NSString *)password
{
	NSData *passwordData = [password dataUsingEncoding:NSUTF8StringEncoding];
	NSDictionary *query = @{
		(__bridge id)kSecClass:       (__bridge id)kSecClassGenericPassword,
		(__bridge id)kSecAttrService: @"OsiriX HTTP Server",
		(__bridge id)kSecAttrAccount: @"OsiriX"
	};
	OSStatus status = SecItemCopyMatching((__bridge CFDictionaryRef)query, NULL);
	if (status == errSecItemNotFound) {
		NSMutableDictionary *item = [query mutableCopy];
		[item setObject:passwordData forKey:(__bridge id)kSecValueData];
		[item setObject:@"OsiriX password" forKey:(__bridge id)kSecAttrDescription];
		status = SecItemAdd((__bridge CFDictionaryRef)item, NULL);
		[item release];
	} else if (status == errSecSuccess) {
		NSDictionary *update = @{ (__bridge id)kSecValueData: passwordData };
		status = SecItemUpdate((__bridge CFDictionaryRef)query, (__bridge CFDictionaryRef)update);
	}
	return (status == errSecSuccess);
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#pragma mark Identity:
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/**
 * This method creates a new identity, and adds it to the keychain.
 * An identity is simply a certificate (public key and public information) along with a matching private key.
 * This method generates a new private key, and then uses the private key to generate a new self-signed certificate.
**/
+ (void)createNewIdentity
{
	// Declare any Carbon variables we may create
	// We do this here so it's easier to compare to the bottom of this method where we release them all
	CFArrayRef outItems = NULL;
	
	// Configure the paths where we'll create all of our identity files
	NSString *basePath = [DDKeychain applicationTemporaryDirectory];
	
	NSString *privateKeyPath  = [basePath stringByAppendingPathComponent:@"private.pem"];
	NSString *reqConfPath     = [basePath stringByAppendingPathComponent:@"req.conf"];
	NSString *certificatePath = [basePath stringByAppendingPathComponent:@"certificate.crt"];
	NSString *certWrapperPath = [basePath stringByAppendingPathComponent:@"certificate.p12"];
	
	// You can generate your own private key by running the following command in the terminal:
	// openssl genrsa -out private.pem 1024
	//
	// Where 1024 is the size of the private key.
	// You may used a bigger number.
	// It is probably a good recommendation to use at least 1024...
	
	NSArray *privateKeyArgs = [NSArray arrayWithObjects:@"genrsa", @"-out", privateKeyPath, @"1024", nil];
	
	NSTask *genPrivateKeyTask = [[[NSTask alloc] init] autorelease];
	
	[genPrivateKeyTask setLaunchPath:@"/usr/bin/openssl"];
	[genPrivateKeyTask setArguments:privateKeyArgs];
    [genPrivateKeyTask launch];
	
	// Don't use waitUntilExit - I've had too many problems with it in the past
	do {
		[NSThread sleepUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.05]];
	} while([genPrivateKeyTask isRunning]);
	
	// Now we want to create a configuration file for our certificate
	// This is an optional step, but we do it so people who are browsing their keychain
	// know exactly where the certificate came from, and don't delete it.
	
	NSMutableString *mStr = [NSMutableString stringWithCapacity:500];
	[mStr appendFormat:@"%@\n", @"[ req ]"];
	[mStr appendFormat:@"%@\n", @"distinguished_name  = req_distinguished_name"];
	[mStr appendFormat:@"%@\n", @"prompt              = no"];
	[mStr appendFormat:@"%@\n", @""];
	[mStr appendFormat:@"%@\n", @"[ req_distinguished_name ]"];
	[mStr appendFormat:@"%@\n", @"C                   = BR"];
	[mStr appendFormat:@"%@\n", @"ST                  = SC"];
	[mStr appendFormat:@"%@\n", @"L                   = Florianopolis"];
	[mStr appendFormat:@"%@\n", @"O                   = Horos Team"];
	[mStr appendFormat:@"%@\n", @"OU                  = Open Source"];
	[mStr appendFormat:@"%@\n", @"CN                  = Horos HTTP Server"];
	[mStr appendFormat:@"%@\n", @"emailAddress        = horos@horosproject.org"];
	
	[mStr writeToFile:reqConfPath atomically:NO encoding:NSUTF8StringEncoding error:nil];
	
	// You can generate your own certificate by running the following command in the terminal:
	// openssl req -new -x509 -key private.pem -out certificate.crt -text -days 365 -batch
	// 
	// You can optionally create a configuration file, and pass an extra command to use it:
	// -config req.conf
	
	NSArray *certificateArgs = [NSArray arrayWithObjects:@"req", @"-new", @"-x509",
														 @"-key", privateKeyPath,
	                                                     @"-config", reqConfPath,
	                                                     @"-out", certificatePath,
	                                                     @"-text", @"-days", @"365", @"-batch", nil];
	
	NSTask *genCertificateTask = [[[NSTask alloc] init] autorelease];
	
	[genCertificateTask setLaunchPath:@"/usr/bin/openssl"];
	[genCertificateTask setArguments:certificateArgs];
    [genCertificateTask launch];
	
	// Don't use waitUntilExit - I've had too many problems with it in the past
	do {
		[NSThread sleepUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.05]];
	} while([genCertificateTask isRunning]);
	
	// Mac OS X has problems importing private keys, so we wrap everything in PKCS#12 format
	// You can create a p12 wrapper by running the following command in the terminal:
	// openssl pkcs12 -export -in certificate.crt -inkey private.pem -passout pass:password -out certificate.p12 -name "Open Source"
	
	NSArray *certWrapperArgs = [NSArray arrayWithObjects:@"pkcs12", @"-export", @"-export",
														 @"-in", certificatePath,
	                                                     @"-inkey", privateKeyPath,
	                                                     @"-passout", @"pass:password",
	                                                     @"-out", certWrapperPath,
	                                                     @"-name", @"OsiriX HTTP Server",
														nil];
	
	NSTask *genCertWrapperTask = [[[NSTask alloc] init] autorelease];
	
	[genCertWrapperTask setLaunchPath:@"/usr/bin/openssl"];
	[genCertWrapperTask setArguments:certWrapperArgs];
    [genCertWrapperTask launch];
	
	// Don't use waitUntilExit - I've had too many problems with it in the past
	do {
		[NSThread sleepUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.05]];
	} while([genCertWrapperTask isRunning]);
	
	// At this point we've created all the identity files that we need
	// Our next step is to import the identity into the keychain
	// We can do this by using the SecKeychainItemImport() method.
	// But of course this method is "Frozen in Carbonite"...
	// So it's going to take us 100 lines of code to build up the parameters needed to make the method call
	NSData *certData = [NSData dataWithContentsOfFile:certWrapperPath];
	
	/* SecKeyImportExportFlags - typedef uint32_t
	 * Defines values for the flags field of the import/export parameters.
	 * 
	 * enum 
	 * {
	 *    kSecKeyImportOnlyOne        = 0x00000001,
	 *    kSecKeySecurePassphrase     = 0x00000002,
	 *    kSecKeyNoAccessControl      = 0x00000004
	 * };
	 * 
	 * kSecKeyImportOnlyOne
	 *     Prevents the importing of more than one private key by the SecKeychainItemImport function.
	 *     If the importKeychain parameter is NULL, this bit is ignored. Otherwise, if this bit is set and there is
	 *     more than one key in the incoming external representation,
	 *     no items are imported to the specified keychain and the error errSecMultipleKeys is returned.
	 * kSecKeySecurePassphrase
	 *     When set, the password for import or export is obtained by user prompt. Otherwise, you must provide the
	 *     password in the passphrase field of the SecKeyImportExportParameters structure.
	 *     A user-supplied password is preferred, because it avoids having the cleartext password appear in the
	 *     application’s address space at any time.
	 * kSecKeyNoAccessControl
	 *     When set, imported private keys have no access object attached to them. In the absence of both this bit and
	 *     the accessRef field in SecKeyImportExportParameters, imported private keys are given default access controls
	**/
	
	SecKeyImportExportFlags importFlags = kSecKeyImportOnlyOne;

	SecItemImportExportKeyParameters importParameters;
	memset(&importParameters, 0, sizeof(importParameters));
	importParameters.version = SEC_KEY_IMPORT_EXPORT_PARAMS_VERSION;
	importParameters.flags = importFlags;
	importParameters.passphrase = CFSTR("password");
	importParameters.keyUsage = NULL;      // NULL = default (any)
	importParameters.keyAttributes = NULL; // NULL = default

	SecExternalFormat inputFormat = kSecFormatPKCS12;
	SecExternalItemType itemType = kSecItemTypeUnknown;


	OSStatus err = 0;
	err = SecItemImport((CFDataRef)certData,   // CFDataRef importedData
						NULL,                  // CFStringRef fileNameOrExtension
						&inputFormat,          // SecExternalFormat *inputFormat
						&itemType,             // SecExternalItemType *itemType
						0,                     // SecItemImportExportFlags flags (Unused)
						&importParameters,     // const SecItemImportExportKeyParameters *keyParams
						NULL,                  // SecKeychainRef importKeychain (NULL = default)
						&outItems);            // CFArrayRef *outItems

	NSLog(@"OSStatus: %i", (int) err);

	NSLog(@"SecExternalFormat: %@", [DDKeychain stringForSecExternalFormat:inputFormat]);
	NSLog(@"SecExternalItemType: %@", [DDKeychain stringForSecExternalItemType:itemType]);

	NSLog(@"outItems: %@", (NSArray *)outItems);

	SecIdentityRef identity = (SecIdentityRef)[(NSArray *)outItems lastObject];
	[DDKeychain KeychainAccessSetPreferredIdentity:identity forName:@"org.horosproject.horoswebserver" keyUse:0];
	
	// Don't forget to delete the temporary files
	[[NSFileManager defaultManager] removeItemAtPath:privateKeyPath error:NULL];
	[[NSFileManager defaultManager] removeItemAtPath:reqConfPath error:NULL];
	[[NSFileManager defaultManager] removeItemAtPath:certificatePath error:NULL];
	[[NSFileManager defaultManager] removeItemAtPath:certWrapperPath error:NULL];
	
	// Don't forget to release anything we may have created
	// (keychain ref removed — SecItemImport(NULL) uses default keychain)
	if(outItems)   CFRelease(outItems);
}

/**
 * Returns an array containing the matching SecIdentityRef for the Horos web server.
 * Uses SecItemCopyMatching and filters by certificate subject summary prefix.
**/
+ (NSArray *)SSLIdentityAndCertificates
{
	NSMutableArray *result = [NSMutableArray array];
	NSDictionary *query = @{
		(__bridge id)kSecClass:      (__bridge id)kSecClassIdentity,
		(__bridge id)kSecMatchLimit: (__bridge id)kSecMatchLimitAll,
		(__bridge id)kSecReturnRef:  @YES
	};
	CFTypeRef items = NULL;
	if (SecItemCopyMatching((__bridge CFDictionaryRef)query, &items) == errSecSuccess && items) {
		NSArray *identities = (__bridge_transfer NSArray *)items;
		for (id obj in identities) {
			SecIdentityRef identityRef = (__bridge SecIdentityRef)obj;
			SecCertificateRef certRef = NULL;
			SecIdentityCopyCertificate(identityRef, &certRef);
			if (certRef) {
				NSString *label = (__bridge_transfer NSString *)SecCertificateCopySubjectSummary(certRef);
				CFRelease(certRef);
				if ([label hasPrefix:@"org.horosproject.horoswebserver"] && result.count == 0) {
					[result addObject:obj];
				}
			}
		}
	}
	return result;
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#pragma mark Utilities:
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/**
 * Creates (if necessary) and returns a temporary directory for the application.
 *
 * A general temporary directory is provided for each user by the OS.
 * This prevents conflicts between the same application running on multiple user accounts.
 * We take this a step further by putting everything inside another subfolder, identified by our application name.
**/
+ (NSString *)applicationTemporaryDirectory
{
	NSString *userTempDir = NSTemporaryDirectory();
	NSString *appTempDir = [userTempDir stringByAppendingPathComponent:@"OsiriX HTTP Server"];
	
	NSFileManager *fileManager = [NSFileManager defaultManager];
	if([fileManager fileExistsAtPath:appTempDir] == NO)
	{
		[fileManager createDirectoryAtPath:appTempDir withIntermediateDirectories:YES attributes:nil error:NULL];
	}
	
	return appTempDir;
}

/**
 * Simple utility class to convert a SecExternalFormat into a string suitable for printing/logging.
**/
+ (NSString *)stringForSecExternalFormat:(SecExternalFormat)extFormat
{
	switch(extFormat)
	{
		case kSecFormatUnknown              : return @"kSecFormatUnknown";
			
		/* Asymmetric Key Formats */
		case kSecFormatOpenSSL              : return @"kSecFormatOpenSSL";
		case kSecFormatSSH                  : return @"kSecFormatSSH - Not Supported";
		case kSecFormatBSAFE                : return @"kSecFormatBSAFE";
			
		/* Symmetric Key Formats */
		case kSecFormatRawKey               : return @"kSecFormatRawKey";
			
		/* Formats for wrapped symmetric and private keys */
		case kSecFormatWrappedPKCS8         : return @"kSecFormatWrappedPKCS8";
		case kSecFormatWrappedOpenSSL       : return @"kSecFormatWrappedOpenSSL";
		case kSecFormatWrappedSSH           : return @"kSecFormatWrappedSSH - Not Supported";
		case kSecFormatWrappedLSH           : return @"kSecFormatWrappedLSH - Not Supported";
			
		/* Formats for certificates */
		case kSecFormatX509Cert             : return @"kSecFormatX509Cert";
			
		/* Aggregate Types */
		case kSecFormatPEMSequence          : return @"kSecFormatPEMSequence";
		case kSecFormatPKCS7                : return @"kSecFormatPKCS7";
		case kSecFormatPKCS12               : return @"kSecFormatPKCS12";
		case kSecFormatNetscapeCertSequence : return @"kSecFormatNetscapeCertSequence";
			
		default                             : return @"Unknown";
	}
}

/**
 * Simple utility class to convert a SecExternalItemType into a string suitable for printing/logging.
**/
+ (NSString *)stringForSecExternalItemType:(SecExternalItemType)itemType
{
	switch(itemType)
	{
		case kSecItemTypeUnknown     : return @"kSecItemTypeUnknown";
			
		case kSecItemTypePrivateKey  : return @"kSecItemTypePrivateKey";
		case kSecItemTypePublicKey   : return @"kSecItemTypePublicKey";
		case kSecItemTypeSessionKey  : return @"kSecItemTypeSessionKey";
		case kSecItemTypeCertificate : return @"kSecItemTypeCertificate";
		case kSecItemTypeAggregate   : return @"kSecItemTypeAggregate";
		
		default                      : return @"Unknown";
	}
}


+ (NSString *)stringForError:(OSStatus)status;
{
	CFStringRef msg = SecCopyErrorMessageString(status, NULL);
	NSString *errorMsg = [NSString stringWithString:(NSString*)msg];
	CFRelease(msg);
	
	return errorMsg;
}

# pragma mark Keychain Access


+ (NSArray *)KeychainAccessCertificatesList {
    
    CFTypeRef   arrayRef     = NULL;
    NSDictionary * dict = @{
                            (id) kSecClass: (id) kSecClassIdentity,
                            (id) kSecMatchLimit: (id) kSecMatchLimitAll,
                            (id) kSecReturnAttributes: (id) kCFBooleanTrue,
                            (id) kSecReturnRef: (id) kCFBooleanTrue,
                            };
    
    OSStatus err = SecItemCopyMatching((CFDictionaryRef) dict, &arrayRef);

    if (err != errSecSuccess) {
        if (err == errSecItemNotFound)
            return [NSArray array];
        NSLog(@"%@:%s: SecItemCopyMatching failed: %@", [[self class] description],
              __PRETTY_FUNCTION__, [DDKeychain stringForError:err]);
        return nil;
    }
    
    NSMutableArray * found = [NSMutableArray array];
    
    for(int i = 0; i < CFArrayGetCount(arrayRef); i++) {
        NSDictionary * attr = (__bridge NSDictionary *)(CFArrayGetValueAtIndex(arrayRef, i));
        /*NSString * label = (NSString *)[attr objectForKey:(id)kSecAttrLabel];*/
        
        if (YES)  {
            SecIdentityRef identityRef = (__bridge SecIdentityRef)([attr objectForKey:(id)kSecValueRef]);
            SecCertificateRef certRef;
            err = SecIdentityCopyCertificate(identityRef, &certRef);
            if (err != errSecSuccess) {
                NSLog(@"%@:%s: SecIdentityCopyCertificate failed: %@ (skipping %@)", [[self class] description],
                      __PRETTY_FUNCTION__, [DDKeychain stringForError:err], identityRef);
                goto skip;
            }

            NSDictionary * valRef = CFBridgingRelease(SecCertificateCopyValues(certRef, nil, nil));

            
            // Skip certs which cannot be used. Page 29 of ITU-T Rec. X.509 (11/2008):
            //
            // KeyUsage  ::=  BIT STRING {
            //    digitalSignature  (0),
            //    contentCommitment (1),
            //    keyEncipherment   (2),
            //    dataEncipherment  (3),
            //    keyAgreement      (4),
            //    keyCertSign       (5),
            //    cRLSign           (6),
            //    encipherOnly      (7),
            //    decipherOnly      (8),
            //
            NSDictionary * keyUsage = [valRef objectForKey:(__bridge id)(kSecOIDKeyUsage)];
            NSInteger flag = keyUsage ? [[keyUsage objectForKey:@"value"] integerValue] : 0;
            
            CFBooleanRef invisible = (CFBooleanRef) [valRef objectForKey:(__bridge id)(kSecAttrIsInvisible)];
            
            // Value of 0 is implies any use - seems to be passed by apple if none is set.
            //
            if (invisible == kCFBooleanTrue)
                goto skip;
            
            if ((flag != 0)&& ((flag & 1) == 0))
                goto skip;
                
                [found addObject:(__bridge id)(identityRef)];
        skip:
            CFRelease(certRef);
        }
    };
    if (arrayRef)
        CFRelease(arrayRef);
    if (searchList)
        CFRelease(searchList);

    return found;
}

+ (void)KeychainAccessExportTrustedCertificatesToDirectory:(NSString*)directory;
{
	BOOL isDirectory, directoryExists;
	
	directoryExists = [[NSFileManager defaultManager] fileExistsAtPath:directory isDirectory:&isDirectory];
	if(directoryExists) return;
	if(!directoryExists)[[NSFileManager defaultManager] createDirectoryAtPath:directory withIntermediateDirectories:NO attributes:nil error:nil];
		
	int domains[3] = {kSecTrustSettingsDomainUser, kSecTrustSettingsDomainAdmin, kSecTrustSettingsDomainSystem};
	
	CFArrayRef certArray = NULL;
	OSStatus status;
	CFIndex numCerts, dex;
	int i;
	for (i=0; i<3; i++)
	{
		status = SecTrustSettingsCopyCertificates(domains[i], &certArray);
		if(status) cssmPerror("SecTrustSettingsCopyCertificates", status);
		
		if( certArray)
		{
			numCerts = CFArrayGetCount(certArray);

			for(dex=0; dex<numCerts; dex++)
			{
				SecCertificateRef certRef = (SecCertificateRef)CFArrayGetValueAtIndex(certArray, dex);			
				CFDataRef certificateDataRef = NULL;
				status = SecItemExport(certRef, kSecFormatX509Cert, kSecItemPemArmour, NULL, &certificateDataRef);
				
				if(status==0)
				{
					NSString *path = [directory stringByAppendingPathComponent:[NSString stringWithFormat:@"%d_%d.pem", i, (int) dex]];
					if(![[NSFileManager defaultManager] fileExistsAtPath:path])
						[(NSData*)certificateDataRef writeToFile:path atomically:YES];
				}
				else NSLog(@"SecItemExport : error : %@", [DDKeychain stringForError:status]);
				
			}
			
			CFRelease(certArray);
			certArray = NULL;
		}
	}
}

// Returns a reference to the preferred identity, or NULL if none was found.
// Call the CFRelease function to release this object when you are finished with it.
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
+ (SecIdentityRef)KeychainAccessPreferredIdentityForName:(NSString*)name keyUse:(int)keyUse;
{
	SecIdentityRef identity = NULL;
	OSStatus status = SecIdentityCopyPreference((CFStringRef)name, keyUse, NULL, &identity);
	if(status!=0) NSLog(@"KeychainAccessPreferredIdentityForName:%@ keyUse: error: %@", name, [DDKeychain stringForError:status]);
	return identity;
}

+ (void)KeychainAccessSetPreferredIdentity:(SecIdentityRef)identity forName:(NSString*)name keyUse:(int)keyUse;
{
	if(identity)
	{
		OSStatus status = SecIdentitySetPreference(identity, (CFStringRef)name, keyUse);
		if(status!=0) NSLog(@"KeychainAccessSetPreferredIdentity:forName:keyUse: error: %@", [DDKeychain stringForError:status]);
	}
}
#pragma clang diagnostic pop

+ (NSString*)KeychainAccessCertificateCommonNameForIdentity:(SecIdentityRef)identity;
{
	NSString *name = nil;
	if(identity)
	{		
		SecCertificateRef certificateRef = NULL;
		SecIdentityCopyCertificate(identity, &certificateRef);
		if(certificateRef)
		{
			CFStringRef commonName = NULL;
			OSStatus status = SecCertificateCopyCommonName(certificateRef, &commonName);
			if(status==0)
			{
				name = [NSString stringWithString:(NSString*)commonName];
				CFRelease(commonName);
			}
			else NSLog(@"KeychainAccessCertificateCommonNameForIdentity: error: %@", [DDKeychain stringForError:status]);
			
			CFRelease(certificateRef);
		}		
	}	
	return name;
}

/*
 * Returns the correct icon for a certificate:
 *   - gold icon for self-signed certificates (subject == issuer)
 *   - blue icon for standard certificates
 */
+ (NSImage*)KeychainAccessCertificateIconForIdentity:(SecIdentityRef)identity
{
	NSImage *icon = nil;
	if (!identity) return nil;
	SecCertificateRef certRef = NULL;
	SecIdentityCopyCertificate(identity, &certRef);
	if (certRef) {
		NSData *subject = (__bridge_transfer NSData *)SecCertificateCopyNormalizedSubjectSequence(certRef);
		NSData *issuer  = (__bridge_transfer NSData *)SecCertificateCopyNormalizedIssuerSequence(certRef);
		CFRelease(certRef);
		BOOL selfSigned = (subject && issuer && [subject isEqualToData:issuer]);
		icon = selfSigned ? [NSImage imageNamed:@"CertSmallRoot.tif"]
		                  : [NSImage imageNamed:@"CertSmallStd.tif"];
	}
	return icon;
}

+ (NSArray*)KeychainAccessCertificateChainForIdentity:(SecIdentityRef)identity
{
	if (!identity) return nil;
	SecCertificateRef certRef = NULL;
	SecIdentityCopyCertificate(identity, &certRef);
	if (!certRef) return nil;

	SecPolicyRef sslPolicy = SecPolicyCreateSSL(true, NULL);
	SecTrustRef trust = NULL;
	NSArray *returnedValue = nil;

	OSStatus status = SecTrustCreateWithCertificates(
		(__bridge CFTypeRef)@[(__bridge id)certRef], sslPolicy, &trust);
	if (status == errSecSuccess && trust) {
		CFErrorRef evalError = NULL;
		SecTrustEvaluateWithError(trust, &evalError);
		if (evalError) CFRelease(evalError);

		CFArrayRef chain = SecTrustCopyCertificateChain(trust);
		if (chain) {
			returnedValue = (__bridge_transfer NSArray *)chain;
		}
		CFRelease(trust);
	}
	CFRelease(sslPolicy);
	CFRelease(certRef);
	return returnedValue;
}


+ (void)KeychainAccessExportCertificateForIdentity:(SecIdentityRef)identity toPath:(NSString*)path;
{
	if([[NSFileManager defaultManager] fileExistsAtPath:path]) return;
	
	SecCertificateRef certificate = NULL;
	OSStatus status = SecIdentityCopyCertificate(identity, &certificate);
	if(status==0)
	{
		CFDataRef certificateDataRef = NULL;
		status = SecItemExport(certificate, kSecFormatX509Cert, kSecItemPemArmour, NULL, &certificateDataRef);
		
		if(status==0)
		{
			[(NSData*)certificateDataRef writeToFile:path atomically:YES];
		}
		else NSLog(@"SecItemExport : error : %@", [DDKeychain stringForError:status]);
		
		CFRelease(certificate);	
	}
	else NSLog(@"SecIdentityCopyCertificate : error : %@", [DDKeychain stringForError:status]);	
}

+ (void)KeychainAccessExportPrivateKeyForIdentity:(SecIdentityRef)identity toPath:(NSString*)path cryptWithPassword:(NSString*)password;
{
	if([[NSFileManager defaultManager] fileExistsAtPath:path]) return;
		
	SecKeyRef privateKey = NULL;
	OSStatus status = SecIdentityCopyPrivateKey(identity, &privateKey);
	if(status==0)
	{
		CFDataRef privateKeyDataRef = NULL;
		SecItemImportExportKeyParameters exportParameters;
		memset(&exportParameters, 0, sizeof(exportParameters));
		exportParameters.passphrase = (CFStringRef)password;
		
		status = SecItemExport(privateKey, kSecFormatPKCS12, 0, &exportParameters, &privateKeyDataRef);
		
		if(status==0)
		{
			[(NSData*)privateKeyDataRef writeToFile:[path stringByAppendingPathExtension:@"p12"] atomically:YES];
			
			// convert the private key file from PKCS#12 format to PEM format:
			// $ openssl pkcs12 -in key.p12 -out key.pem -passin pass:passwordIN -passout pass:passwordOUT
			
			NSArray *args = [NSArray arrayWithObjects:	@"pkcs12",
							 @"-in", [path stringByAppendingPathExtension:@"p12"],
							 @"-out", path,
							 @"-passin", [NSString stringWithFormat:@"pass:%@", password],
							 @"-passout", [NSString stringWithFormat:@"pass:%@", password], nil];
			
			NSTask *convertTask = [[[NSTask alloc] init] autorelease];
			[convertTask setLaunchPath:@"/usr/bin/openssl"];
			[convertTask setArguments:args];
			[convertTask launch];
			
            while( [convertTask isRunning])
                [NSThread sleepForTimeInterval: 0.1];
            
			[[NSFileManager defaultManager] removeItemAtPath:[path stringByAppendingPathExtension:@"p12"] error:NULL]; // remove the .p12 file
		}
		else NSLog(@"SecItemExport : error : %@", [DDKeychain stringForError:status]);
		
		CFRelease(privateKey);
	}
	else NSLog(@"SecIdentityCopyPrivateKey : error : %@", [DDKeychain stringForError:status]);			
}

+ (void)KeychainAccessOpenCertificatePanelForIdentity:(SecIdentityRef)identity;
{
	if(identity)
	{		
		SecCertificateRef certificateRef = NULL;
		SecIdentityCopyCertificate(identity, &certificateRef);
		if(certificateRef)
		{
			NSMutableArray *certificates = [NSMutableArray arrayWithObject:(id)certificateRef];
			NSArray *certificateChain = [DDKeychain KeychainAccessCertificateChainForIdentity:identity];
			[certificates addObjectsFromArray:certificateChain];
			
			[[SFCertificatePanel sharedCertificatePanel] runModalForCertificates:certificates showGroup:YES];		
			CFRelease(certificateRef);
		}
	}
}

#pragma mark-

// Returns a reference to the preferred identity for DICOM TLS, or NULL if none was found.
// Call the CFRelease function to release this object when you are finished with it.
+ (SecIdentityRef)identityForLabel:(NSString*)label;
{
	return [DDKeychain KeychainAccessPreferredIdentityForName:label keyUse:0];
}

+ (NSString*)certificateNameForLabel:(NSString*)label;
{
	SecIdentityRef identity = [DDKeychain identityForLabel:label];
	
	NSString *name = nil;
	if(identity)
	{
		name = [NSString stringWithString:[DDKeychain KeychainAccessCertificateCommonNameForIdentity:identity]];
		CFRelease(identity);
	}
	
	return name;
}

+ (NSImage*)certificateIconForLabel:(NSString*)label;
{
	SecIdentityRef identity = [DDKeychain identityForLabel:label];
	
	NSImage *icon = nil;
	if(identity)
	{
		icon = [DDKeychain KeychainAccessCertificateIconForIdentity:identity];
		CFRelease(identity);
	}
	
	return icon;
}

+ (void)openCertificatePanelForLabel:(NSString*)label;
{
	SecIdentityRef identity = [DDKeychain identityForLabel:label];
	if(identity)
	{
		[DDKeychain KeychainAccessOpenCertificatePanelForIdentity:identity];
		CFRelease(identity);
	}
}

#pragma mark Other Utilities

+ (void)generatePseudoRandomFileToPath:(NSString*)path;
{
	NSPoint mouseLocation = [NSEvent mouseLocation];
	NSTimeInterval time = [[NSDate date] timeIntervalSince1970];

	NSString *string = [NSString stringWithFormat:@"%f%f%lf", mouseLocation.x, mouseLocation.y, time];
	[string writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:nil];
}

+ (void)lockFile:(NSString*)path;
{
	if(!lockedFiles) lockedFiles = [[NSMutableDictionary dictionary] retain];
	
	@synchronized( lockedFiles)
	{
		int n=0;
		
		if([[lockedFiles allKeys] containsObject:path])
		{
			n = [(NSNumber*)[lockedFiles objectForKey:path] intValue];
		}
		
		[lockedFiles setObject:[NSNumber numberWithInt:n+1] forKey:path];
		NSLog(@"lockFile: %d %@", n+1, path);
	}
}

+ (void)unlockFile:(NSString*)path;
{	
	@synchronized( lockedFiles)
	{
		int n=0;
		
		if(lockedFiles)
		{
			if([[lockedFiles allKeys] containsObject:path])
			{
				n = [(NSNumber*)[lockedFiles objectForKey:path] intValue];
				n--;
				[lockedFiles setObject:[NSNumber numberWithInt:n] forKey:path];
				NSLog(@"unlockFile: %d %@", n, path);
			}
		}
		
		if(n==0)
		{
			[lockedFiles removeObjectForKey:path];
			//[[NSFileManager defaultManager] removeItemAtPath:path error:NULL];
			//NSLog(@"removeItemAtPath: %@", path);
		}
	}
}

+ (void)lockTmpFiles;
{
	if(!lockFile) lockFile = [[NSRecursiveLock alloc] init];
	
	[lockFile lock];
}

+ (void)unlockTmpFiles;
{
	[lockFile unlock];
	//NSString *cmd = [NSString stringWithFormat:@"rm %@* %@*", TLS_PRIVATE_KEY_FILE, TLS_CERTIFICATE_FILE];
	//system([cmd cStringUsingEncoding:NSUTF8StringEncoding]);
}


@end
