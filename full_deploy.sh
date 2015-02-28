#!/bin/sh
# @author Joschi <josua.krause@gmail.com>
# created 2015-02-27 10:39

if [ -z `git branch | grep "* master"` ]; then
  echo "not on master"
  exit 1
fi

echo "not done yet!"
exit 1

git checkout gh-pages && git merge master
if [ $? -ne 0 ]; then
  exit 1
fi

./setup.sh --clean --default --convert "9F6F484429DDCC04 AE056C5933AFED18 298C80CC2F7CEDC4 EB704BFBAB4E2B86 B7ECA3897A4AD00D A9BD9D012E87A360 4EF051B883DE5192 998093F33FE2D940 CDBF9E622DEE5B07 AEF023C2029F05BC"
if [ $? -ne 0 ]; then
  exit 1
fi

git add -f json/9F6F484429DDCC04.json json/AE056C5933AFED18.json json/298C80CC2F7CEDC4.json json/EB704BFBAB4E2B86.json json/B7ECA3897A4AD00D.json json/A9BD9D012E87A360.json json/4EF051B883DE5192.json json/998093F33FE2D940.json json/CDBF9E622DEE5B07.json json/AEF023C2029F05BC.json json/dictionary.json patients.txt
if [ $? -ne 0 ]; then
  exit 1
fi

git commit -m "update"

git push origin gh-pages && git checkout master



