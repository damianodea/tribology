#!/bin/bash

root_dir=$(pwd)
root_dir=$(basename $root_dir)

if [[ ! $root_dir =~ "SCS" ]]
then
	echo "You are launching this script inside $(pwd), please launch the program inside SCS root directory"
	echo "bash Chek_status_labelling.sh"
	exit
fi

#Get current iteration number
ite=$( ls -t Iterations/ | head -n 1)

for sys in Iterations/$ite/Exploration/*
do
	echo $(basename $sys)
	check_dir=$sys/SAMPLED

	#Count number of pwi
	n_pwis=$(ls -1 ${check_dir}/*.pwi | wc -l)
	echo "Number of pwi: $n_pwis"

	#Count number of pwos
	n_pwos=$(ls -1 ${check_dir}/*.pwo | wc -l)
	echo "Number of pwo: $n_pwos"

	n_not_pwos=$(grep -L 'P=' $check_dir/*.pwo | wc -l)
	echo "Number of pwo not converged: $n_not_pwos"

	if test $n_pwos -lt $n_pwis
	then
		echo "Labelling phase is not finished, resuming..."
		continue
	elif test $n_pwos -gt $n_pwis
	then
		echo "Something unexpected happened, number of pwos is greater than number of pwis"
		continue
	fi

	if test $n_not_pwos -lt 0
	then
		echo "Labelling is finished"
		continue
	fi

	for n_pwo in $(grep -L 'P=' $check_dir/*.pwo)
	do
		n_pwi=${n_pwo//.pwo/.pwi}
		beta=($(grep 'beta' $n_pwi))
		beta=${beta[2]}
		maxstep=($(grep 'electron_maxstep' $n_pwi))
		maxstep=${maxstep[2]}
		echo "Beta value: $beta"
		echo "Maxstep value: $maxstep"
		
		if test $# -gt 1
		then
			#Awk needed to print decimal numbers with leading zero
			new_beta=$( echo "scale=6; $beta*0.5" | bc -l | awk '{printf "%.6f", $0}')
			new_maxstep=$( echo "$maxstep + 100" | bc -l)
			echo "Replacing not converged pwi to better beta params"

			#In case of bad substitution use these 2 lines
			##sed -i "s/.*beta.*/mixing_beta = 0.05 /" $n_pwi
					##sed -i "s/.*electron_maxstep.*/electron_maxstep = 500 /" $n_pwi

			sed -i "s/.*beta.*/mixing_beta = $new_beta /" $n_pwi
			sed -i "s/.*electron_maxstep.*/electron_maxstep = $new_maxstep /" $n_pwi
			grep 'beta' $n_pwi
			grep 'electron_maxstep' $n_pwi
			rm $n_pwo
		fi 
	done
done
