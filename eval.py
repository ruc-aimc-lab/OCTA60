#!/usr/bin/env python3
import argparse
import json
import math
import statistics
import os
from pathlib import Path


MEE_THRESHOLD = 20
MAE_THRESHOLD = 50
AUC_MAX_THRESHOLD = 25
IMG_SIZE = 2912


def calculate_pair_errors(target_points, predicted_points):
    assert(len(target_points) == len(predicted_points))
    errors = []
    for target, predicted in zip(target_points, predicted_points):
        if len(predicted) == 0:
            dist = math.inf
        else:
            dist = math.hypot(predicted[0] - target[0], predicted[1] - target[1])
        errors.append(dist)
    return statistics.median(errors), max(errors), statistics.mean(errors)


def calculate_auc(mean_errors):
    success_rates = []
    for threshold in range(1, AUC_MAX_THRESHOLD + 1):
        successful_pairs = 0
        for mean_error in mean_errors:
            if mean_error < threshold:
                successful_pairs += 1
        success_rate = successful_pairs / len(mean_errors)
        success_rates.append(success_rate)
    return statistics.mean(success_rates)


def print_eval_res(results):
    total_pairs = results["total_pairs"]
    for status in ("failed", "inaccurate", "acceptable"):
        count = results[status]
        rate = count / total_pairs
        print(f"{status.capitalize()} rate: {rate:.2f}")
    print(f"AUC@25: {results['auc25']:.3f}")


class OCTA60:
    def __init__(self, data_path='./'):
        self.data_path = data_path
        self.version = 'mmm26'
        imset_file = os.path.join(self.data_path, 'ImageSets', 'OCTA60.txt')
        self.imset = [x.strip() for x in open(imset_file).readlines() if x.strip()]
        self.target_points = [None]*len(self.imset)
        for i,img_id in enumerate(self.imset):
            self.target_points[i] = self._read_target_points(img_id)

    def _read_target_points(self, img_id):
        anno_file = os.path.join(self.data_path, 'Annotations', self.version, f'{img_id}.txt')
        target_points = []
        for line in open(anno_file):
            columns = line.split()
            x = float(columns[2]) * IMG_SIZE
            y = float(columns[3]) * IMG_SIZE
            target_points.append((x, y))
        return target_points

    def _evaluate(self, predictions):
        assert(len(self.target_points) == len(predictions))
        failed_count = 0
        inaccurate_count = 0
        acceptable_count = 0
        mean_errors = []

        for i,img_id in enumerate(self.imset):
            predicted_points = predictions.get(img_id)
            if len(predicted_points) == 0:
                failed_count += 1
                mean_errors.append(math.inf)
                continue
            median_error, maximum_error, mean_error = calculate_pair_errors(self.target_points[i],  [(p[0] * IMG_SIZE, p[1] * IMG_SIZE) if p else () for p in predicted_points])
            mean_errors.append(mean_error)

            if median_error < MEE_THRESHOLD and maximum_error < MAE_THRESHOLD:
                acceptable_count += 1
            else:
                inaccurate_count += 1

        return {
            "total_pairs": len(self.imset),
            "failed": failed_count,
            "inaccurate": inaccurate_count,
            "acceptable": acceptable_count,
            "auc25": calculate_auc(mean_errors),
        }

    def run(self, pred_file):
        predictions = json.loads(Path(pred_file).read_text())
        results = self._evaluate(predictions)
        return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCTA60 based evaluation")
    parser.add_argument(
        "pred_file", type=Path,
        help="prediction made by your method in JSON format, see CARe.json",
    )
    args = parser.parse_args()

    eval = OCTA60()
    results = eval.run(args.pred_file)
    print_eval_res(results)
