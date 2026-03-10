.PHONY: Horos clean

CONFIG ?= Debug
DERIVED_DATA ?= build
DESTINATION ?= platform=macOS,arch=arm64

Horos:
	xcodebuild -project "Horos.xcodeproj" -scheme Horos -configuration "$(CONFIG)" -derivedDataPath "$(DERIVED_DATA)" -destination "$(DESTINATION)"

clean:
	@rm -rf ./build
