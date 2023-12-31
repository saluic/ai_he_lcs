from sklearn.metrics import roc_curve, auc, confusion_matrix
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time
import sys
import os
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

# Constants
N_PREDICTION_YEARS = 6

OPERATOR_DICT = {
    'e'     :   '==',
    'g'     :   '>',
    'l'     :   '<',
    'ge'    :   '>=',
    'le'    :   '<='
}

# Global rounding: the number of digits to the right of the decimal point
# when rounding, throughout this script.
GR = 5

def main():
    print("Sybil Evaluation")

    # ArgParse library is used to manage command line arguments.
    parser = argparse.ArgumentParser(
        epilog="Example: sybil_eval.py \
        path/to/actual.csv path/to/prediction.csv -o output_dir \
        -f gender:2:e race:2:e -c 0.25 0.5 0.75"
    )
    parser.add_argument("actual", help="a CSV file generated by \
        cleanup_nlst_for_sybil.py which contains the actual values regarding \
        the presence of cancer n years after a given CT scan.")
    parser.add_argument("prediction", help="a CSV file generated by main.py \
        (utilized by Sybil container image) which contains the prediction \
        values generated by Sybil regarding the probability of cancer n years \
        after a given CT scan.")
    parser.add_argument('-o', "--outdir", help="A directory in which to \
        generate the output. \
        Default: script current working directory.",
        default=os.getcwd())
    parser.add_argument('-f', "--filters", help="Any number of filters to \
        apply to the data, formated as such: property_name:value:operator, \
        e.g. race:2:e. Operator options: \
        e -> equal, g -> greater than, l -> less than, \
        ge -> greater than or equal to, le -> less than or equal to. \
        Default: no filters.", 
        nargs='+', default=[])
    parser.add_argument('-c', '--cutoffs', help="Any number of probability \
        cutoffs to be used for the generation of multiple confusion matrices. \
        Default: Youden's J index", type=float,
        nargs='+', default=None)
    args = parser.parse_args()
    print("Actual:", args.actual)
    print("Prediction:", args.prediction)
    print("Output directory:", args.outdir)
    print("Filters:", args.filters)
    print("Cutoffs:", args.cutoffs)

    # Read in CSVs
    actual = pd.read_csv(args.actual)
    prediction = pd.read_csv(args.prediction)

    # Filter the actual CSV
    if len(args.filters) > 0:
        actual_filtered = parse_filters(actual, args.filters)
    else:
        actual_filtered = actual

    # Initialize new actual dataframe
    actual_aligned = []
    prediction_aligned = []

    # Iterate through the filtered CSV
    for index, row in actual_filtered.iterrows():
        query_str = ""
        # Find entries with the same PID
        query_str += "pid == " + str(row["pid"]) + " and "
        # Find entries with the same screening year
        query_str += "study_yr == " + str(row["study_yr"])
        queried_prediction = prediction.query(query_str)
        n_predictions = queried_prediction.shape[0]

        # There are multiple CT scans per individual patient per study year.
        # Because of this, the actual data and prediction data don't align.
        # Thus, repeated actual data columns must be generated to match the
        # prediction data.
        actual_values = []
        for year in range(1,N_PREDICTION_YEARS+1):
            column_name = "canc_yr" + str(year)
            actual_value = row[column_name]
            actual_values.append(actual_value)
        for repeat in range(n_predictions):
            actual_aligned.append(actual_values)

        # Add the prediction probability values to the aligned DataFrame.
        for index in range(n_predictions):
            prediction_values = []
            for year in range(1,N_PREDICTION_YEARS+1):
                column_name = "pred_yr" + str(year)
                prediction_value = queried_prediction.iloc[index][column_name]
                prediction_values.append(prediction_value)
            prediction_aligned.append(prediction_values)
   
    # Create DataFrames
    # These dataframes can now be compared-
    # year1 of the actual aligned df can be compared with year1 of the
    # prediction aligned df, year2 with year2, and so on.
    column_names = ["year" + str(i) for i in range(1,N_PREDICTION_YEARS+1)]
    actual_aligned_df = pd.DataFrame(
        actual_aligned, columns = column_names
    )
    prediction_aligned_df = pd.DataFrame(
        prediction_aligned, columns = column_names
    )
    
    print(f"Number of associated CT DICOMs: {prediction_aligned_df.shape[0]}")

    # Check that we have a non-zero number of entries after filtering and
    # aligning. If not, exit script.
    if actual_aligned_df.shape[0] == 0:
        print("There are no entries left in actual values after filtering. " +
            "Quitting.")
        return
    if prediction_aligned_df.shape[0] == 0:
        print("There are no entries left in prediction values after aligning" +
            " to actual values. Quitting.")
        return

    # Create output directory named based on filters.
    output_directory = args.outdir + '/' + generate_dir_name(args.filters)
    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    # Execute function to generate multi-ROC curve, generates PNG.
    optimal_cutoffs = generate_multi_roc(
        actual_aligned_df,
        prediction_aligned_df,
        output_directory
    )

    # Execute function to generate multiple confusion matrices, generates one
    # CSV file per prediction year.
    if args.cutoffs:
        generate_confusion_matrices(
            actual_aligned_df,
            prediction_aligned_df,
            output_directory,
            args.cutoffs,
            mode = "all"
        )
    else:
        generate_confusion_matrices(
            actual_aligned_df,
            prediction_aligned_df,
            output_directory,
            optimal_cutoffs,
            mode = "one_each"
        )

def generate_dir_name(filters: list[str]) -> str:
    # This function generates the name of the output directory depending on the
    # filters used in the command line arguments.
    output = "sybil_eval"
    if len(filters) == 0:
        return output + "_no_filters"
    for index, filt in enumerate(filters):
        output += '_'
        filter_clean = filt.replace(':', '')
        filter_clean = filter_clean.replace('_', '')
        output += filter_clean
    return output


def parse_filters(df: pd.DataFrame, filters: list[str]) -> pd.DataFrame:
    # This function applies user-selected filters to given DataFrame.
    # Example: race:2:e will return a DataFrame which contains only rows where
    # the associated patient has a race=2 (Black).
    # EXAMPLE BREAKDOWN:
    # race:2:e
    # race = the column to use for filtering
    # 2 = the value used for comparison
    # e = the chosen comparison operator, in this case 'equal to'
    # The filter therefore selects only individuals whose race is equal to 2.

    query_str = ""
    for index in range(len(filters)):
        parse_list = filters[index].split(':')
        appended_str = ""
        
        # Add property name
        # Ensure valid property name
        if parse_list[0] not in df.columns:
            columns_str = ', '.join(df.columns)
            raise Exception("Invalid property name found in filter " \
                f"{filters[index]}: {parse_list[0]}. " \
                "\nPlease select a property name from the following list: " \
                f"\n{columns_str}")
        appended_str += parse_list[0] + " "

        # Add operator
        # Ensure valid operator
        if parse_list[2] not in OPERATOR_DICT.keys():
            operators_str = ', '.join(OPERATOR_DICT.keys())
            raise Exception("Invalid operator found in filter " \
                f"({filters[index]}): {parse_list[2]}. " \
                "\nPlease select an operator from the following list: " \
                f"\n{operators_str}")
        appended_str += OPERATOR_DICT[parse_list[2]] + " "

        # Add value
        appended_str += parse_list[1]

        # Add 'and'
        if index != len(filters) - 1:
            appended_str += " and "

        query_str += appended_str
    print(f"Query: {query_str}")
    output = df.query(query_str)
    print(f"Number of entries satisfying query: {output.shape[0]}")
    return df.query(query_str)      

def generate_multi_roc(actual, prediction, out_dir):
    # This function uses actual and prediction values to create a multi-ROC
    # curve PNG image, which it then stores in a specified output directory.
    # The generated image is labeled such that each curve is identified by year,
    # and area under curve (AUC) value is provided for each curve.
    
    print("Generating Multi-ROC curve...")

    # Can return a list of cutoffs determined by maximizing the Youden’s
    # J index, or equivalently, the sum of sensitivity and specificity, across
    # all points of the ROC curve.
    # One cutoff per ROC curve.
    output = []
    plt.figure(figsize = (5, 5), dpi = 100)
    for year in actual:
        current_actual = actual[year].tolist()
        current_prediction = prediction[year].tolist()
        fpr, tpr, threshold = roc_curve(current_actual, current_prediction)
        # Calculate Area Under Curve (AUC), round to nearest 5 decimal points.
        roc_auc = round(auc(fpr, tpr), GR)

        optimal_cutoff = threshold[np.argmax(tpr - fpr)]
        output.append(optimal_cutoff)

        plt.plot(fpr, tpr, linestyle = "-",
            label = f"{year}: AUC = {roc_auc}")

    plt.xlabel("1 - Specificity")
    plt.ylabel("Sensitivity")
    plt.title("Sybil Performance", loc = "center")
    plt.legend(loc = "lower right")

    file_name = "multi_roc.png"
    plt.savefig(out_dir + "/" + file_name)
    return output

def generate_confusion_matrices(actual, prediction, out_dir, cutoffs,
    mode='one_each'):
    # This function uses actual and prediction values to create multiple
    # confusion matrices using the provided cutoffs (thresholds).
    
    print("Generating confusion matrices...")
    print(f"Cutoffs: {cutoffs}")

    if mode not in ["all", "one_each"]:
        print("Invalid value for parameter \"mode\": use \"all\" or " +
            "\"one_each\".")
        return
    # Interchangeable modes:
    # all: uses every cutoff for each prediction year.
    # one_each: one cutoff is used for one prediction year, so the number of
    # cutoffs should be equal to the number of prediction years.

    if mode == "one_each":
        if prediction.shape[1] != len(cutoffs):
            print("Mode \"one_each\": The number of cutoffs selected is " +
                "not equal to the number of prediction years.")
            return

    for index, year in enumerate(actual):
        csv_name = "confusion_matrices_" + year + ".csv"
        with open(out_dir + "/" + csv_name, 'w') as current_csv:
            if mode == "all":
                for cutoff in cutoffs:
                    matrix_csv = counts_to_matrix(
                        actual[year], prediction[year], cutoff)
                    current_csv.write(matrix_csv)
            elif mode == "one_each":
                matrix_csv = counts_to_matrix(
                    actual[year], prediction[year], cutoffs[index])
                current_csv.write(matrix_csv)
    
def counts_to_matrix(truth, prediction, cutoff):
    # This function accepts a truth array, prediction array, and cutoff, then
    # returns a string in CSV format representing a confusion matrix with
    # additional descriptive statistics:
    # Sensitivity, Specificity, Accuracy, Positive Predictive Value, and
    # Negative Predictive Value.
    
    output = f"Probability cutoff,=,{round(cutoff, GR)}\n"
    pred = np.where(prediction > cutoff, 1, 0)
    tn, fp, fn, tp = confusion_matrix(truth, pred).ravel()
    total = tn+fp+fn+tp

    # Write confusion matrix
    output += ",actual_positive,actual_negative\n"
    output += f"prediction_positive,{tp},{fp}\n"
    output += f"prediction_negative,{fn},{tn}\n"

    # Calculate descriptive values
    sensitivity = round(tp/(tp+fn), GR) if (tp+fn) != 0 else "DIV0"
    specificity = round(tn/(tn+fp), GR) if (tn+fp) != 0 else "DIV0"

    accuracy = round((tp+tn)/total, GR) if total != 0 else "DIV0"
    # Positive Predictive Value
    ppv = round(tp/(tp+fp), GR) if (tp+fp) != 0 else "DIV0"
    # Negative Predictive Value
    npv = round(tn/(tn+fn), GR) if (tn+fn) != 0 else "DIV0"

    # Write values
    output += f"Sensitivity,=,{sensitivity}\n"
    output += f"Specificity,=,{specificity}\n"
    output += f"Accuracy,=,{accuracy}\n"
    output += f"PPV,=,{ppv}\n"
    output += f"NPV,=,{npv}\n\n"

    return output

start = time.perf_counter()
main()
end = time.perf_counter()
print(f"{sys.argv[0]} Completed in {end - start:0.4f} seconds.")

