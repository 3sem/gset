import socket
import os
import argparse
import subprocess
import struct
import sys
from embedding import *
from shuffler import *
import numpy as np
from numpy import linalg
from subprocess import *
from random import choice


class sl_kernel:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-d", "--dataset", dest="dataset_path", required=True)
        self.parser.add_argument("-e", "--embeddings", dest="emb_path", required=True)
        self.parser.add_argument("-o", dest="out_file", required=False, default="")

        self.args = self.parser.parse_args()

        self.parse_dataset(self.args.dataset_path)
        self.parse_embeddings(self.args.emb_path)

        self.actions_lib = setuplib()
        set_check_loop(self.actions_lib, 0)

    def parse_dataset(self, dataset_path):
        with open(dataset_path, "rb") as f:
            data = f.read()
            pack_start = 0
            embedding_arr = []
            fit_arr = []
            passes_arr = []
            while True:
                emb = struct.unpack("f" * 149, data[pack_start : pack_start + 149 * 4])[
                    :-2
                ]
                len_passes = struct.unpack(
                    "i", data[pack_start + 149 * 4 : pack_start + 149 * 4 + 4]
                )[0]
                passes_start = pack_start + 149 * 4 + 4
                passes = data[passes_start : passes_start + len_passes]
                fitness = struct.unpack(
                    "f", data[passes_start + len_passes : passes_start + len_passes + 4]
                )[0]
                sep_start = passes_start + len_passes + 4
                sep = struct.unpack("i", data[sep_start : sep_start + 4])[0]
                if sep != 0xB0BA:
                    print("File parse failed")
                    exit(1)
                pack_start = sep_start + 4
                embedding_arr.append(list(emb))
                fit_arr.append(fitness)
                passes_arr.append(passes)
                if pack_start >= len(data):
                    break

        self.data_embedding = np.array(embedding_arr)
        self.data_fit = np.array(fit_arr)
        good_points = np.where(self.data_fit > 0.1)
        self.data_embedding = self.data_embedding[good_points]
        row_mods = np.sqrt((self.data_embedding * self.data_embedding).sum(axis=1))
        self.data_embedding = self.data_embedding / row_mods[:, np.newaxis]
        self.data_fit = self.data_fit[good_points]
        self.data_passes = np.array(passes_arr)[good_points]

    def parse_embeddings(self, emb_path):
        self.embeddings = []
        with open(emb_path, "rb") as f:
            data = f.read()
            unpacked = struct.iter_unpack("f" * 147 + "i", data)
            for emb in unpacked:
                if emb[-1] != 0xB0BA:
                    print("Failed to parse embeddings", file=sys.stderr)
                    exit(1)
                self.embeddings.append(emb[:-1])

    def choose_passes(self):
        self.from_hist_seq(hist_len=2)

    def weighted_sum_dists(self):
        test_embedding = np.array(self.embeddings)
        row_mods = np.sqrt((test_embedding * test_embedding).sum(axis=1))
        test_embedding = test_embedding / row_mods[:, np.newaxis]
        dists = self.compute_dists(self.data_embedding, test_embedding)
        sizes = np.array(self.sizes)
        sizes = sizes[:, np.newaxis]
        sizes_norm = sizes / np.max(sizes)
        fit_norm = self.data_fit / np.max(self.data_fit)
        dists = dists / sizes_norm
        dists = dists / fit_norm
        sum_dists = np.add.reduce(dists)
        num_lists = 1
        idx = np.argpartition(sum_dists, num_lists)
        self.top_lists = self.data_passes[idx[:num_lists]]

    def max_size_min_dist(self):
        test_embedding = np.array(self.embeddings)
        row_mods = np.sqrt((test_embedding * test_embedding).sum(axis=1))
        test_embedding = test_embedding / row_mods[:, np.newaxis]
        dists = self.compute_dists(self.data_embedding, test_embedding)
        sizes = np.array(self.sizes)
        ind = np.argmax(sizes)
        list_ind = np.argmin(dists[ind, :])
        self.top_lists = [self.data_passes[list_ind]]

    def from_hist_seq(self, hist_len=3):
        self.map_emb_on_dataset()
        hist_deep = self.build_freq_seq(hist_len=hist_len)
        hist_shallow = self.build_freq_seq(hist_len=1)
        final_list = ["ccp"]
        pass_seq_len = 100
        for _ in range(pass_seq_len):
            if len(final_list) < hist_len or tuple(final_list[-hist_len:]) not in hist_deep:
                hist_entry = hist_shallow[(final_list[-1],)]
                new_pass = self.get_new_pass_from_hist(hist_entry, final_list, hist_len)
                final_list.append(new_pass)
            else:
                hist_entry = hist_deep[tuple(final_list[-hist_len:])]
                new_pass = self.get_new_pass_from_hist(hist_entry, final_list, hist_len)
                if new_pass == None:
                    hist_entry = hist_shallow[(final_list[-1],)]
                    new_pass = self.get_new_pass_from_hist(hist_entry, final_list, hist_len)
                final_list.append(new_pass)
        final_list.extend(["sccp", "*record_bounds", "ivcanon", "cunroll", "lim"])
        self.top_lists = [" ".join(final_list).encode()]

    def get_new_pass_from_hist(self, hist_entry, passes_list, hist_len):
        sorted_passes = sorted(hist_entry, key=hist_entry.get, reverse=True)
        for pass_name in sorted_passes:
            if pass_name == passes_list[-1]:
                continue
            if valid_pass_seq(self.actions_lib, passes_list + [pass_name], 2) != 0:
                continue
            if ' '.join(passes_list[-hist_len+1:] + [pass_name]) in ' '.join(passes_list):
                continue
            return pass_name
        return None

    def compute_dists(self, data, test):
        num_data = data.shape[0]
        num_test = test.shape[0]
        dists = np.zeros((num_test, num_data))
        X_squared = np.tile(np.add.reduce(test * test, 1), (num_data, 1)).transpose()
        X_train_squared = np.tile(np.add.reduce(data * data, 1), (num_test, 1))
        dists = np.sqrt(
            np.abs(X_squared + X_train_squared - 2 * test @ data.transpose())
        )
        return dists

    def expand_pass_list(self):
        self.final_list = self.top_lists[0]
        print(self.final_list)
        self.final_list = self.final_list.decode().split()
        indented_pass_list = []
        for pass_name in self.final_list[:-5]:
            if pass_name == "none_pass":
                continue
            if pass_name == "fix_loops":
                indented_pass_list.append("fix_loops")
                indented_pass_list.append("loop")
                indented_pass_list.append(">loopinit")
                for inpass_name in self.final_list[-5:]:
                    if inpass_name == "none_pass":
                        continue
                    indented_pass_list.append(">" + inpass_name)
                indented_pass_list.append(">cdce")
                indented_pass_list.append(">loopdone")
                indented_pass_list.append("crited")
            else:
                indented_pass_list.append(pass_name)

        self.final_list = indented_pass_list

    def get_sizes(self):
        self.sizes = []
        for emb in self.embeddings:
            self.sizes.append(emb[6])

    def main(self):
        self.get_sizes()
        self.choose_passes()
        print("Chosen pass list")
        self.expand_pass_list()
        print(self.final_list)
        if self.args.out_file != '':
            with open(self.args.out_file, 'w') as f:
                f.write("\n".join(self.final_list))
        print(len(self.final_list))

    def map_emb_on_dataset(self):
        test_embedding = np.array(self.embeddings)
        row_mods = np.sqrt((test_embedding * test_embedding).sum(axis=1))
        test_embedding = test_embedding / row_mods[:, np.newaxis]
        dists = self.compute_dists(self.data_embedding, test_embedding)
        min_ind = np.argmin(dists, axis=1)
        self.mapped_embeddings = [self.data_embedding[x] for x in min_ind]
        self.mapped_passes = [self.data_passes[x] for x in min_ind]

    def build_freq_seq(self, hist_len=3):
        split_passes = [
            [y.decode() for y in x if y.decode() != "none_pass"]
            for x in [x.split()[:-5] for x in self.mapped_passes]
        ]
        hist_table = {}
        for pass_seq in split_passes:
            for ind in range(hist_len, len(pass_seq)):
                hist_piece = tuple(pass_seq[ind - hist_len : ind])
                if hist_piece in hist_table:
                    if pass_seq[ind] in hist_table[hist_piece]:
                        hist_table[hist_piece][pass_seq[ind]] += 1
                    else:
                        hist_table[hist_piece][pass_seq[ind]] = 1
                else:
                    hist_table[hist_piece] = {}
                    hist_table[hist_piece][pass_seq[ind]] = 1
        return hist_table


if __name__ == "__main__":
    kernel = sl_kernel()
    try:
        kernel.main()
    except (Exception, SystemExit, KeyboardInterrupt) as e:
        raise e
