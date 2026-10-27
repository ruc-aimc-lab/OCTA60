#!/usr/bin/env python3
import argparse
import json
import math
import os


class PredictionFormatChecker:
    def __init__(self, data_path='./'):
        self.data_path = data_path
        self.errors = []

    def _error(self, location, problem, fix):
        self.errors.append(f"{location}: {problem}\n  Fix: {fix}")

    def _load_annotations(self):
        image_set = os.path.join(self.data_path, "ImageSets/OCTA60.txt")
        if not os.path.isfile(image_set) or not os.access(image_set, os.R_OK):
            self._error(image_set, "Image ID file Error.", "DownLoad Correct ImageSets/OCTA60.txt with readable permission.")
            return None

        ids = []
        with open(image_set) as file:
            for line in file:
                ids.append(line.strip())
        if not ids or len(ids) != len(set(ids)):
            self._error(str(image_set), "The reference ID list Error.", "DownLoad Correct ImageSets/OCTA60.txt.")
            return None

        point_pairs_counts = {}
        for image_id in ids:
            path = os.path.join(self.data_path, "Annotations", "mmm26", f"{image_id}.txt")
            try:
                with open(path) as file:
                    lines = file.readlines()
            except Exception as error:
                self._error(path, str(error), "Download the correct annotation file for this image ID.")
                continue
            if not lines:
                self._error(str(path), "The annotation file is empty.", "Download the correct annotation file for this image ID.")
            for number, line in enumerate(lines):
                try:
                    values = [float(value) for value in line.split()]
                    valid = len(values) == 4 and all(0 <= value <= 1 for value in values)
                except:
                    valid = False
                if not valid:
                    self._error(f"{path}:{number+1}", "Invalid reference annotation row.", 
                                "Download the correct annotation file for this image ID; each row must contain four numbers in [0, 1].")
            point_pairs_counts[image_id] = len(lines)
        
        return point_pairs_counts

    def _load_pred_file(self, pred_file):
        if not os.path.exists(pred_file) or not os.path.isfile(pred_file) or not os.access(pred_file, os.R_OK):
            self._error(pred_file, "Pred File Error.", "Provide the correct prediction file path with readable permission.")
            return None

        with open(pred_file, encoding="utf-8") as file:
            pairs = json.load(file, object_pairs_hook=tuple)

        predictions = {}
        for image_id, points in pairs:
            if image_id in predictions:
                self._error(f"JSON key {repr(image_id)}", "Duplicate key.", "Keep exactly one entry per image ID; do not repeat JSON keys.")
            predictions[image_id] = points
        return predictions

    def _check_prediction_points_format(self, image_id, predicted_points, expected_count):
        if not isinstance(predicted_points, list):
            self._error(f"Image ID {repr(image_id)}", "Format Error", "The predicted point lists must be a JSON array.")
            return None
        if not predicted_points:
            return None
        if len(predicted_points) != expected_count:
            self._error(f"Image ID {repr(image_id)}", f"Expected {expected_count} point entries, found {len(predicted_points)}.",
                        "Keep one entry per annotation row in the same order; use [] for each missing point.")

        for index, point in enumerate(predicted_points):
            point_path = f"{repr(image_id)}[{index}] (row {index + 1})"
            if point == []:
                continue
            if not isinstance(point, list) or len(point) != 2:
                self._error(f"{point_path}", "Point Cord Format Error",
                            "Provide exactly two coordinates in x, y order, or use [] for a missing point.")
                continue
            for axis, value in zip(("x", "y"), point):
                if type(value) not in (int, float):
                    self._error(f"{point_path}.{axis}", "Point Cord Format Error", f"Expected a number, found {type(value).__name__}.")
                    continue
                if not math.isfinite(value):
                    self._error(f"{point_path}.{axis}", "Point Cord Format Error", "Use a finite number, or [] for a missing point.")

    def check(self, pred_file):
        self.errors = []
        point_pairs_counts = self._load_annotations()
        if self.errors:
            return self._print_result()

        predictions = self._load_pred_file(pred_file)
        if self.errors:
            return self._print_result()

        missing = sorted(set(point_pairs_counts) - predictions.keys())
        if missing:
            self._error("$", f"Missing image IDs: {', '.join(missing)}.", 'Add these missing IDs.')
            return self._print_result()

        for image_id, count in point_pairs_counts.items():
            self._check_prediction_points_format(image_id, predictions[image_id], count)
        if self.errors:
            return self._print_result()

        print(f"PASS: {pred_file} | Prediction File format is valid.")
        return True

    def _print_result(self):
        print(f"FAIL: {len(self.errors)} error(s) found.")
        for number, error in enumerate(self.errors, 1):
            print(f"{number}. {error}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCTA60 prediction format check")
    parser.add_argument(
        "pred_file",
        help="prediction made by your method in JSON format, see WrappedSourcePoints/CARe.json",
    )
    args = parser.parse_args()

    checker = PredictionFormatChecker()
    passed = checker.check(args.pred_file)
