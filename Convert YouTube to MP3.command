#!/bin/zsh
cd "/Users/xerogi/Documents/mp3 converter" || exit 1
clear
echo "YouTube -> MP3 converter"
echo "Output folder: /Users/xerogi/Documents/Music/Beats"
echo
mkdir -p "/Users/xerogi/Documents/Music/Beats"
"/Users/xerogi/Documents/mp3 converter/.venv/bin/python" converter.py
echo
echo "Press Enter to close this window."
read
