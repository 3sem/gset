#!/bin/bash
ln -s test_code/ benchmark_link
python3 emb_collector.py \
  -b="-O2 1.c dir1/2.c -o benchmark_link/a.out" --plugin ./lib/plugin.so \
  -g /usr/bin/gcc-7 \
  -o ./benchmark_link/ \
  --verbose
unlink benchmark_link
