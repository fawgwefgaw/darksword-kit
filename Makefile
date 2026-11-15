# DarkSword-Kit — 构建
# 
# 1) kexploit（真实内核利用，需 macOS + Xcode）:
#      make kexploit SDK=iphoneos
#    产物 build/kexploit，需 ldid 用 entitlements.plist 签名
#
# 2) 语法检查（任何有 clang 的环境）:
#      make syntax-check

SDK ?= iphoneos
CC ?= clang

XCODE_SDK_PATH = $(shell xcrun --sdk $(SDK) --show-sdk-path 2>/dev/null)

kexploit:
	@mkdir -p build
	$(CC) -arch arm64 -isysroot $(XCODE_SDK_PATH) \
	      -framework Foundation -framework IOSurface \
	      -O2 -Wall -std=gnu11 \
	      -o build/kexploit kexploit/main.m
	@echo "[make] build/kexploit done — 记得签名:"
	@echo "       ldid -Skexploit/entitlements.plist build/kexploit"

syntax-check:
	@mkdir -p build
	@for f in src/*.c; do $(CC) -std=c11 -fsyntax-only $$f && echo "OK $$f"; done

clean:
	rm -rf build

.PHONY: kexploit syntax-check clean
