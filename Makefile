VERSION=\"v0.0.1\"
CC = gcc
CFLAGS = -O3 -s -mtune=native -Wall -DVERSION=$(VERSION) -Wextra
DEST = /usr/local/bin/

all: output_dir bin/strstream bin/filter_melting_range bin/strstreamone bin/sequence_end_points

output_dir: 
	mkdir -p bin
bin/strstream: src/strstream.c
	$(CC) src/strstream.c -o bin/strstream $(CLIBS) $(CFLAGS)
bin/strstreamone: src/strstreamone.c
	$(CC) src/strstreamone.c -o bin/strstreamone $(CLIBS) $(CFLAGS)
bin/sequence_end_points: src/sequence_end_points.c
	$(CC) src/sequence_end_points.c -o bin/sequence_end_points $(CLIBS) $(CFLAGS)
bin/filter_melting_range: src/filter_melting_range.c
	$(CC) src/filter_melting_range.c -o bin/filter_melting_range $(CLIBS) $(CFLAGS)

clean:
	rm -vf bin/* -Rv

install: all
	install -c bin/strstream bin/filter_melting_range bin/strstreamone SelectiveGenomeAmplification src/select_mers.py src/score_mers.py src/filter_max_consecutive_binding.py $(DEST)

