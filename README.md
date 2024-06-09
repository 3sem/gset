## GIMPLE Standalone Embedding Tool (GSET)
Инструмент для построения эмбеддингов функций языка C.
GSET основан на инструментарии пакетов автоматизированной настройки оптимизирующей компиляции GCC PHO [1].

### Состав проекта

- emb_collector.py -- точка входа пользоватемя. Реализует функциональность настройки инфраструктуры, сборки, преобразования и сохранения эмбеддингов для дальнейшего использования
- embedding -- пакет рассчета эмбеддинга. Внешняя зависимость от репозитория в MCCS-Group [2]
- sl_wrapper.py -- обертка, управляющая процессом компиляции. Взаимодействие между компилятором и основной логикой GSET происходит через Unix-сокеты
- lib/plugin.so -- плагин для GCC, осуществляющий взаимодействие с менеджером проходов GCC. В данном проекте используется предварительно собранный как динамическая библиотека плагин из GCC PHO [1].
Гарантирована поддержка GCC 7.3-7.5 из транка GNU, таким образом, можно не собирать компилятор, а установить посредством apt.
На других версиях GCC не тестировалось
- env_preset_run.sh -- пример использования на исходных кодах, размещенных в test_code
- src_processing/ -- вспомогательная функциональность. Например, извлечение имен функций и исходного кода.
### Литература
1) Отращенко А. И., Акимов З. Д., Ефанов Н. Н. Разработка средства оптимизации встраиваемого ПО на базе автонастройки перестановкой оптимизационных проходов современного компилятора GCC // "Труды МФТИ" Том 16, № 1 (61) (2024), cc 44-59
2) MIPT MCCS-Group Repositories: https://github.com/mccs-group

### Использование
Основной сценарий (пример):

```
#!/bin/bash
ln -s test_code/ benchmark_link # создать символическую ссылку на бенчмарк
python3 emb_collector.py \
  -b="-O2 1.c dir1/2.c -o benchmark_link/a.out" --plugin ./lib/plugin.so \
  -g /usr/bin/gcc-7 \
  -o ./benchmark_link/ \
  --verbose
unlink benchmark_link # уничтожить символическую ссылку на бенчмарк
```

Пример из "реального бенчмарка" (557xz из SPEC2017 и Multibenches):

```
#!/bin/bash
ln -s ../multibenches/557xz/ benchmark_link
python3 emb_collector.py \
  -b="-O2 -std=c99 -z muldefs -DSPEC -DSPEC_CPU -DNDEBUG -DSPEC_AUTO_BYTEORDER=0x12345678 -DHAVE_CONFIG_H=1 -DSPEC_MEM_IO -DSPEC_XZ -DSPEC_AUTO_SUPPRESS_OPENMP -I. -Ispec_mem_io -Isha-2 -Icommon -Iliblzma/api -Iliblzma/lzma -Iliblzma/common -Iliblzma/check -Iliblzma/simple -Iliblzma/delta -Iliblzma/lz -Iliblzma/rangecoder -fno-strict-aliasing -DSPEC_LP64 spec.c spec_xz.c pxz.c common/tuklib_physmem.c liblzma/common/common.c liblzma/common/block_util.c liblzma/common/easy_preset.c liblzma/common/filter_common.c liblzma/common/hardware_physmem.c liblzma/common/index.c liblzma/common/stream_flags_common.c liblzma/common/vli_size.c liblzma/common/alone_encoder.c liblzma/common/block_buffer_encoder.c liblzma/common/block_encoder.c liblzma/common/block_header_encoder.c liblzma/common/easy_buffer_encoder.c liblzma/common/easy_encoder.c liblzma/common/easy_encoder_memusage.c liblzma/common/filter_buffer_encoder.c liblzma/common/filter_encoder.c liblzma/common/filter_flags_encoder.c liblzma/common/index_encoder.c liblzma/common/stream_buffer_encoder.c liblzma/common/stream_encoder.c liblzma/common/stream_flags_encoder.c liblzma/common/vli_encoder.c liblzma/common/alone_decoder.c liblzma/common/auto_decoder.c liblzma/common/block_buffer_decoder.c liblzma/common/block_decoder.c liblzma/common/block_header_decoder.c liblzma/common/easy_decoder_memusage.c liblzma/common/filter_buffer_decoder.c liblzma/common/filter_decoder.c liblzma/common/filter_flags_decoder.c liblzma/common/index_decoder.c liblzma/common/index_hash.c liblzma/common/stream_buffer_decoder.c liblzma/common/stream_decoder.c liblzma/common/stream_flags_decoder.c liblzma/common/vli_decoder.c liblzma/check/check.c liblzma/check/crc32_table.c liblzma/check/crc32_fast.c liblzma/check/crc64_table.c liblzma/check/crc64_fast.c liblzma/check/sha256.c liblzma/lz/lz_encoder.c liblzma/lz/lz_encoder_mf.c liblzma/lz/lz_decoder.c liblzma/lzma/lzma_encoder.c liblzma/lzma/lzma_encoder_presets.c liblzma/lzma/lzma_encoder_optimum_fast.c liblzma/lzma/lzma_encoder_optimum_normal.c liblzma/lzma/fastpos_table.c liblzma/lzma/lzma_decoder.c liblzma/lzma/lzma2_encoder.c liblzma/lzma/lzma2_decoder.c liblzma/rangecoder/price_table.c liblzma/delta/delta_common.c liblzma/delta/delta_encoder.c liblzma/delta/delta_decoder.c liblzma/simple/simple_coder.c liblzma/simple/simple_encoder.c liblzma/simple/simple_decoder.c liblzma/simple/x86.c liblzma/simple/powerpc.c liblzma/simple/ia64.c liblzma/simple/arm.c liblzma/simple/armthumb.c liblzma/simple/sparc.c xz/args.c xz/coder.c xz/file_io.c xz/hardware.c xz/list.c xz/main.c xz/message.c xz/options.c xz/signals.c xz/util.c common/tuklib_open_stdxxx.c common/tuklib_progname.c common/tuklib_exit.c common/tuklib_cpucores.c common/tuklib_mbstr_width.c common/tuklib_mbstr_fw.c spec_mem_io/spec_mem_io.c sha-2/sha512.c" --plugin ./lib/plugin.so \
  -g /usr/bin/gcc-7 \
  -o ./benchmark_link/ \
  --verbose
#unlink benchmark_link

```

### Зависимости
#### Системные зависимости:
- Python 3 (тестировалось на 3.9)
- GCC-7 (тестировалось на Trunk GCC-7.5, установленном через apt: 'sudo apt install gcc-7')
- CTags

#### Python-пакеты:
- numpy
- sklearn
- argparse

### Модифицированные Python-пакеты, используемые как third-party:
- functiondefextractor 