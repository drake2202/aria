SHELL := /usr/bin/env bash

PYTHON := $(if $(wildcard .venv/bin/python3),.venv/bin/python3,python3)
PIP := $(if $(wildcard .venv/bin/pip),.venv/bin/pip,$(PYTHON) -m pip)

APP_NAME := aria
ENTRYPOINT := aria_main.py
FLASH_SO := ../flash/libpepflashplayer.so
MAPS_DIR := ../maps

PYI_FLAGS := \
	--noconfirm \
	--onefile \
	--name $(APP_NAME) \
	--collect-all PyQt5.QtWebEngine \
	--collect-all PyQt5.QtWebEngineWidgets \
	--collect-all PyQt5.QtNetwork

ADD_DATA_FLAGS := --add-data $(MAPS_DIR):maps
ifneq (,$(wildcard $(FLASH_SO)))
ADD_DATA_FLAGS += --add-data $(FLASH_SO):flash
endif

.PHONY: help venv deps run build clean distclean install-app uninstall-app aur-srcinfo aur-build aur-install

help:
	@echo "Aria build targets:"
	@echo "  make deps        - install Python dependencies + PyInstaller"
	@echo "  make run         - run client from source"
	@echo "  make build       - build onefile binary at dist/aria"
	@echo "  make install-app - install a user launcher for Rofi/XFCE"
	@echo "  make uninstall-app - remove the user launcher"
	@echo "  make clean       - remove build/dist artifacts"
	@echo "  make distclean   - clean + remove venv"
	@echo "  make aur-srcinfo - regenerate aur/aria-git/.SRCINFO"
	@echo "  make aur-build   - build local package with makepkg"
	@echo "  make aur-install - build + install package with makepkg -si"

venv:
	@if [[ ! -x .venv/bin/python3 ]]; then \
		echo "[make] Creating virtualenv"; \
		python3 -m venv .venv; \
	fi

deps: venv
	@echo "[make] Installing dependencies"
	@$(PIP) install -r requirements.txt pyinstaller

run:
	@echo "[make] Running Aria"
	@$(PYTHON) -m legendonline

install-app:
	@./install-app.sh

uninstall-app:
	@./uninstall-app.sh

build: clean deps
	@echo "[make] Building onefile binary"
	@if [[ ! -f $(FLASH_SO) ]]; then \
		echo "[make] WARNING: $(FLASH_SO) not found; runtime fallback paths will be used"; \
	fi
	@$(PYTHON) -m PyInstaller $(PYI_FLAGS) $(ADD_DATA_FLAGS) $(ENTRYPOINT)
	@echo "[make] Done: $$(pwd)/dist/$(APP_NAME)"
	@ls -lh dist/$(APP_NAME)

clean:
	@rm -rf build dist *.spec

distclean: clean
	@rm -rf .venv

aur-srcinfo:
	@cd aur/aria-git && makepkg --printsrcinfo > .SRCINFO

aur-build:
	@cd aur/aria-git && makepkg -s

aur-install:
	@cd aur/aria-git && makepkg -si
