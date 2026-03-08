#!/bin/bash
pdflatex -interaction=nonstopmode final.tex > pdflatex1.log 2>&1
biber final > biber.log 2>&1
pdflatex -interaction=nonstopmode final.tex > pdflatex2.log 2>&1
echo "Compilation finished."
