# Overview
A script that reads PDF and searches inside provided text or sentences in double quotes

# Prerequirements
* Install Python3
* Install all needed packages with: ```pip3 install -r requirements.txt```

# Script run
Basic output in the CLI:
```
python3 main.py -f example.pdf -t "Test text"
```
or for output into file:
```
python3 main.py -f example.pdf -t "Test text" -o
```
Use ```python3 main.py -h``` for help.

# Script output
Script by default will output information about sites and count of find text in CLI. If you will use -o argument it will save output to the file ```results.txt```
