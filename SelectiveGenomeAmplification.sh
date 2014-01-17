#!/bin/bash
# range of mers, min and max 
: ${min_mer_range=6}
: ${max_mer_range=10}
# max mer distance, the distance between two mers in our selected outputs
: ${max_mer_distance=5000}
# directory to store our counts and sorted counts
: ${counts_directory=$PWD/counts}
# temp directory 
: ${tmp_directory=$PWD/tmp}
# output directory 
: ${output_directory=$PWD/outputs}
# min/maximum kmer melting point
: ${max_melting_temp=30}
: ${min_melting_temp=0}
# minimum mer count
: ${min_mer_count=0}
# maximum mers to pick
: ${max_select=15}
# mers to specifically IGNORE, space delimited
: ${ignore_mers=''}

export ignore_mers
export min_mer_range
export max_mer_range

export max_select

export min_mer_count
export max_mer_distance

export max_melting_temp 
export min_melting_temp 

PATH=$PATH:$PWD

# Make our counts directory
if [ ! -d $counts_directory ]; then
	mkdir $counts_directory
fi

# Make our temporary directory
if [ ! -d $tmp_directory ]; then
	mkdir $tmp_directory
fi

# Make our output directory
if [ ! -d $output_directory ]; then
	mkdir $output_directory
fi

foreground=$1
background=$2

if [[ ! -f $foreground ]]; then
	echo "Could not open $foreground."
	exit 1
fi

if [[ ! -f $background ]]; then
	echo "Could not open $background."
	exit 1
fi

for fasta_file in $foreground $background; do

	counts=$counts_directory/$(basename $fasta_file)
	tmp=$tmp_directory/$(basename $fasta_file)

	echo pre-processing $fasta_file

	# check if our preprocessed file exists
	if [[ ! -f $tmp ]]; then
		echo "> pre processed $fasta_file" >> $tmp
		cat $fasta_file | grep -v "^>" | tr -d '\n' >> $tmp
	fi

	# run counts if they haven't been created 
	rm $counts-counts
	for mer in `seq $min_mer_range $max_mer_range`;	do 
		if [ ! -e $counts-counts-$mer ]; then
			echo checking $mer mers for $fasta_file
			kmer_total_count -i $tmp -k $mer -l -n >> $counts-counts-$mer
		else 
			echo "$mer mers already done for $fasta_file"
		fi
		
		cat $counts-counts-$mer >> $counts-counts
	
	done
done


fg_counts=$counts_directory/$(basename $foreground)-counts
bg_counts=$counts_directory/$(basename $background)-counts

fg_tmp=$tmp_directory/$(basename $foreground)
bg_tmp=$tmp_directory/$(basename $background)

# remove ignored mers
if [ "$ignore_mers" ]; then
	echo "removing ignored mers: " + $ignore_mers
	for mer in $ignore_mers; do
		sed -i '/^'$mer'\t/d' $fg_counts
		sed -i '/^'$mer'\t/d' $bg_counts
	done
fi


echo "checking if mers are below melting temperature in the foreground"
rm $fg_counts-fg-non-melting
melting_range $min_melting_temp $max_melting_temp < $fg_counts > $fg_counts-fg-non-melting &

echo "checking if mers are below melting temperature in the background"
rm $bg_counts-bg-non-melting
melting_range $min_melting_temp $max_melting_temp < $bg_counts > $bg_counts-bg-non-melting

# echo "scoring mer selectivity"
# python ./mer_selectivity.py $fg_counts-fg-non-melting $bg_counts-bg-non-melting

echo ""
echo "scoring mers"
python ./select_mers.py $fg_counts-fg-non-melting $fg_tmp $bg_counts-bg-non-melting $bg_tmp # > $(basename $foreground)_$(basename $background)_final_mers 