import pandas as pd
import time
import sys
import argparse


"""
This script is used to generate ROC curves, AUC, and confusion matrices based
on a variety of user inputs.

It is designed to be specifically utilized with the other scripts in this
project which generate the prerequisite CSVs for this script.
Namely, those scripts are:
main.py (utilized by the Sybil container image).
cleanup_nlst_for_sybil.py (requires nlst clinical data, either via CDAS or the
Cancer Imaging Archive).
"""

def main():
	print("Sybil NLST Filter for ROC curve drawing and AUC calculation")

	# ArgParse library is used to manage command line arguments.`
	parser = argparse.ArgumentParser()
	parser.add_argument("actual", help="a CSV file generated by \
		cleanup_nlst_for_sybil.py which contains the actual values regarding \
		the presence of cancer n years after a given CT scan.")
	parser.add_argument("prediction", help="a CSV file generated by main.py \
		(utilized by Sybil container image) which contains the prediction \
		values generated by Sybil regarding the probability of cancer n years \
		after a given CT scan.")
	parser.add_argument("filters", help="any number of filters to apply to the \
		data, formated as such: property_name:value:operator, e.g. age:65:ge. \
		Operator options: \
		e -> equal, g -> greater than, l -> less than, \
		ge -> greater than or equal to, le -> less than or equal to", 
		nargs='*')
	args = parser.parse_args()
	print("Actual:", args.actual)
	print("Prediction: ", args.prediction)
	print("Filters: ", args.filters)

start = time.perf_counter()
main()
end = time.perf_counter()
print(f"{sys.argv[0]} Completed in {end - start:0.4f} seconds.")
