python3 emb_collector.py \
  -b="-O2 test_code/1.c test_code/dir1/2.c" --plugin ./lib/plugin.so \
  -g /usr/bin/gcc-7 \
  -o ./test_code/
