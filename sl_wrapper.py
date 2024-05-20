import socket
import os
import argparse
import subprocess
import struct
import sys
from embedding import *
import numpy as np


class sl_kernel:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument(
            "--plugin", dest="plugin_path", action="store", required=True
        )
        self.parser.add_argument(
            "-b",
            "--build",
            dest="build_args",
            action="store",
            required=True,
        )
        self.parser.add_argument("-g", "--gcc-name", dest="gcc_name", required=True)
        self.parser.add_argument(
            "--no-optimize-size", action="store_true", dest="no_optimize_size"
        )
        self.parser.add_argument("-d", "--dataset", dest="dataset_path", required=True)

        self.args = self.parser.parse_args()

        self.parse_dataset(self.args.dataset_path)

        self.EMBED_LEN_MULTIPLIER = 200

        self.gcc_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM, 0)
        self.pid = os.getpid()
        while True:
            try:
                self.gcc_socket.bind(f"kernel{self.pid}.soc")
                print("Socket bind is OK")
            except OSError as e:
                sleep(1.5)
		print("OSError while socket binding:", e)
                continue
            break
        self.gcc_socket.settimeout(30)

        self.local_build_string = (
            f"{self.args.gcc_name} -fplugin={self.args.plugin_path} "
            "-fplugin-arg-plugin-collect_embedding "
            f"-fplugin-arg-plugin-remote_socket=kernel{self.pid}.soc "
            f"-fplugin-arg-plugin-socket_postfix={self.pid} "
            f"{self.change_to_local(self.args.build_args)}"
        )

        self.build_string = (
            f"{self.args.gcc_name} -fplugin={self.args.plugin_path} "
            f"-fplugin-arg-plugin-pass_replace{'' if self.args.no_optimize_size else '=set_optimize_size'} "
            f"-fplugin-arg-plugin-pass_file={self.pid}_list2.txt "
            f"{self.args.build_args}"
        )

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

    def choose_passes(self):
        self.max_size_min_dist()

    def weighted_sum_dists(self):
        test_embedding = np.array(list(self.embeddings.values()))
        row_mods = np.sqrt((test_embedding * test_embedding).sum(axis=1))
        test_embedding = test_embedding / row_mods[:, np.newaxis]
        dists = self.compute_dists(self.data_embedding, test_embedding)
        sizes = np.array(list(self.sizes.values()))
        sizes = sizes[:, np.newaxis]
        sizes_norm = sizes / np.max(sizes)
        print(sizes_norm.shape)
        fit_norm = self.data_fit / np.max(self.data_fit)
        dists = dists / sizes_norm
        #dists = dists / fit_norm
        sum_dists = np.add.reduce(dists)
        num_lists = 1
        idx = np.argpartition(sum_dists, num_lists)
        self.top_lists = self.data_passes[idx[:num_lists]]
        print(dists)
        print(sum_dists)

    def max_size_min_dist(self):
        test_embedding = np.array(list(self.embeddings.values()))
        row_mods = np.sqrt((test_embedding * test_embedding).sum(axis=1))
        test_embedding = test_embedding / row_mods[:, np.newaxis]
        dists = self.compute_dists(self.data_embedding, test_embedding)
        sizes = np.array(list(self.sizes.values()))
        ind = np.argmax(sizes)
        list_ind = np.argmin(dists[ind, :])
        self.top_lists = [self.data_passes[list_ind]]


    def compute_dists(self, data, test):
        num_data = data.shape[0]
        num_test = test.shape[0]
        dists = np.zeros((num_test, num_data))
        X_squared = np.tile(np.add.reduce(test * test, 1), (num_data, 1)).transpose()
        X_train_squared = np.tile(np.add.reduce(data * data, 1), (num_test, 1))
        dists = np.sqrt(np.abs(X_squared + X_train_squared - 2 * test @ data.transpose()))
        return dists

    def build_profile(self):
        self.embeddings = {}
        self.gcc_instance = subprocess.Popen(self.local_build_string, shell=True)

        while not os.path.exists(f"gcc_plugin{self.pid}.soc"):
            self.gcc_instance.poll()
            if self.gcc_instance.returncode != None:
                print(
                    f"gcc failed: return code {self.gcc_instance.returncode}\n",
                    file=sys.stderr,
                )
                continue
            pass

        while True:
            try:
                name = self.gcc_socket.recv(4000).decode()
                print(f'Got name {name}')
                embedding = self.get_embedding(wait=True)
                self.embeddings[name] = embedding
            except socket.timeout:
                break

        if self.gcc_instance.wait() != 0:
            print(
                f"gcc failed: return code {self.gcc_instance.returncode}\n",
                file=sys.stderr,
            )

        if self.gcc_instance.returncode != 0:
            exit(self.gcc_instance.returncode)

    def build_final(self):
        with open(f"{self.pid}_list2.txt", "w") as f:
            passes = "\n".join(self.final_list)
            f.write(passes)

        self.gcc_instance = subprocess.Popen(self.build_string, shell=True)

        if self.gcc_instance.wait() != 0:
            print(
                f"gcc failed: return code {self.gcc_instance.returncode}\n",
                file=sys.stderr,
            )

        os.unlink(f"{self.pid}_list2.txt")

        if self.gcc_instance.returncode != 0:
            exit(self.gcc_instance.returncode)

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
        #    size_info = (
        #        run(
        #            f"nm --print-size --size-sort --radix=d .{self.pid}_tmp.out",
        #            shell=True,
        #            capture_output=True,
        #        )
        #        .stdout.decode("utf-8")
        #        .splitlines()
        #    )
        #    self.sizes = {}
        #    for line in size_info:
        #        pieces = line.split()
        #        name = pieces[3].partition(".")[0]
        #        if name in self.embeddings.keys():
        #            self.sizes[name] = int(pieces[1])

        self.sizes = {}
        for name in self.embeddings:
            self.sizes[name] = self.embeddings[name][6]

    def calc_embedding(self, embedding):
        autophase = embedding[:47]
        cfg_len = embedding[47]
        cfg = embedding[48 : 48 + cfg_len]
        val_flow = embedding[48 + cfg_len :]

        cfg_embedding = list(get_flow2vec_embed(cfg, 25))
        val_flow_embedding = list(get_flow2vec_embed(val_flow, 25))

        return autophase + cfg_embedding + val_flow_embedding

    def get_embedding(self, wait=False):
        timeout = self.gcc_socket.gettimeout()
        self.gcc_socket.settimeout(None)
        embedding_msg = self.gcc_socket.recv(
            1024 * self.EMBED_LEN_MULTIPLIER, 0 if wait else socket.MSG_DONTWAIT
        )
        self.gcc_socket.settimeout(timeout)
        embedding = [x[0] for x in struct.iter_unpack("i", embedding_msg)]
        embedding_vec = self.calc_embedding(embedding)
        return embedding_vec

    def change_to_local(self, build_args):
        if "-o" in build_args:
            build_path_index = build_args.find("-o")
            filename_start = build_path_index + 3  # skip '-o' and possible space after
            filename_end = build_args.find(" ", filename_start)
            filename_end = None if filename_end == -1 else filename_end
            filename = build_args[filename_start:filename_end]
            return build_args.replace(filename, f".{self.pid}_tmp.out ")
        else:
            return build_args + f" -o .{self.pid}_tmp.out"

    def main(self):
        print("Kernel start")
        self.build_profile()
        print("Built first time")
        self.get_sizes()
        print("Collected sizes")
        os.unlink(f".{self.pid}_tmp.out")
        self.choose_passes()
        print("Chosen pass list")
        self.expand_pass_list()
        print(self.final_list)
        self.build_final()
        print("Built final")


if __name__ == "__main__":
    kernel = sl_kernel()
    try:
        kernel.main()
    except (Exception, SystemExit, KeyboardInterrupt) as e:
        os.unlink(f"kernel{kernel.pid}.soc")
        raise e

    os.unlink(f"kernel{kernel.pid}.soc")
