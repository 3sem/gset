python3 emb_collector.py \
  -b="DIR=test_code -O2 -o test_code/a.out" --plugin ./lib/plugin.so \
  -g /usr/bin/gcc-7 \
  -o ./test_code/ \
