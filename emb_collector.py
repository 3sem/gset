#! /usr/bin/env python3
import socket
from time import sleep
from pprint import pprint
import datetime
import os
import argparse
import struct
import sys
import subprocess
import json
from embedding import *
from src_processing import postprocessor, preprocessor


class gcc_wrapper:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.verbose = False
        self.parser.add_argument(
            "-b",
            "--build",
            dest="build_args",
            action="store",
            required=True,
        )
        self.parser.add_argument(
            "--plugin", dest="plugin_path", action="store", required=True
        )
        self.parser.add_argument("-g", "--gcc-name", dest="gcc_name", required=True)
        self.parser.add_argument("-o",
            "--output", action="store", dest="output_path", required=True
        )
        self.parser.add_argument('-v', '--verbose',
                            action='store_true')  # on/off flag

        self.args = self.parser.parse_args()
        self.EMBED_LEN_MULTIPLIER = 200
        self.embeddings = {}

        self.gcc_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM, 0)
        self.pid = os.getpid()

        while True:
            try:
                self.gcc_socket.bind(f"kernel{self.pid}.soc")
            except OSError:
                sleep(1.5)
                continue
            break
        self.gcc_socket.settimeout(45)

        if self.args.build_args.startswith("DIR="):
            __dir = self.args.build_args.split("=")[1].split(" ")[0] # format DIR=/path/to/srs <another args>
            argline_tail = " ".join(self.args.build_args.lstrip("DIR=").split(" ")[1:])
            self.args.build_args = " ".join(preprocessor.extract_filenames(__dir)[0]) + " " + argline_tail

        else:
            compiler_args = preprocessor.chdir_build_string(self.args.build_args, self.args.output_path)
            self.args.build_args = compiler_args
        self.build_string = (
            f"{self.args.gcc_name} -fplugin={self.args.plugin_path} "
            "-fplugin-arg-plugin-collect_embedding "
            f"-fplugin-arg-plugin-remote_socket=kernel{self.pid}.soc "
            f"-fplugin-arg-plugin-socket_postfix={self.pid} "
            f"{self.args.build_args}"
        )

        self.gcc_instance = None  # run build_and_save() to assign compiler instance (as subprocess)

    def ifverbose(self, method, args):
        if self.args.verbose:
            return method(args)
        else:
            return None

    def build_and_save(self, config: dict):
        self.gcc_instance = subprocess.Popen(self.build_string, shell=True)
        self.ifverbose(print, ("Log message", "build string:", self.build_string))
        #if "-O2" not in self.args.build_args:
        #    return 0

        self.embeddings = {}
        '''
        while True:
            try:
                name = self.gcc_socket.recv(4000).decode()
                embedding = self.get_embedding(wait=True)
                self.embeddings[name] = embedding
                if self.gcc_instance.poll() != None:
                    self.gcc_socket.settimeout(0)
            except BlockingIOError:
                break
            except socket.timeout:
                break

        if self.gcc_instance.wait() != 0:
            print(
                f"gcc failed: return code {self.gcc_instance.returncode}\n",
                file=sys.stderr,
            )
            os.unlink(f"gcc_plugin{self.pid}.soc")
            exit(self.gcc_instance.returncode)

        if len(self.embeddings) == 0:
            self.ifverbose(print, ("Log message: Warning!", "Embedding list is empty"))
            return 
        '''
        print([k for k in self.embeddings.keys()])
        self.ifverbose(print, "Embeddings calculated for symbols:")
        self.ifverbose(print, [k for k in self.embeddings.keys()])
        self.args.output_path = os.path.normpath(self.args.output_path)
        if self.args.output_path is not None:
            outfile_name = ""
            try:
                if "par_dir" in config['outfile_name_body']:
                    outfile_name += os.path.basename(os.path.normpath(os.getcwd())) + '_'
                if "par_timestamp" in config['outfile_name_body']:
                    outfile_name += str(int(round(datetime.now().timestamp())))
                outfile_name += ".json"
            except:
                outfile_name = "output_embeddings.json"
                self.ifverbose(print, ("Default filename will be used for embeddings saving:", outfile_name))
            fullpath = self.args.output_path + os.sep + outfile_name
            self.ifverbose(print, ("Full path to file for embeddings saving:", fullpath))

            embeddings = {k: {
                'cnt': v[:47],
                'cfg': v[47:47+25],
                'dfg': v[47+25:],
                'full': v[:],
                'sign': None,
                'code': None,
                'file': None,
                'desc': None
            } for k, v in self.embeddings.items()}
            print("embeddings", embeddings)
            preprocessed_data = preprocessor.evaluate_compiler_preprocessing(
                self.args.gcc_name,
                self.args.output_path,
                preprocessor.extract_filenames(os.getcwd(), self.args.build_args),
                verbose=self.args.verbose
            )

            for k, entry in preprocessed_data.items():
                for signature in entry['sign']:
                    embeddings[signature['name']]['sign'] = signature['text_repr']
                    embeddings[signature['name']]['code'] = signature['code']
                    embeddings[signature['name']]['file'] = k

            self.ifverbose(pprint, embeddings)
            with open(fullpath, "w+") as outf:
                json.dump(embeddings, outf)
                outf.flush()
            print("Embeddings are written to:", fullpath)

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

    def calc_embedding(self, embedding):
        autophase = embedding[:47]
        cfg_len = embedding[47]
        cfg = embedding[48: 48 + cfg_len]
        val_flow = embedding[48 + cfg_len :]

        cfg_embedding = list(get_flow2vec_embed(cfg, 25))
        val_flow_embedding = list(get_flow2vec_embed(val_flow, 25))

        return autophase + cfg_embedding + val_flow_embedding


if __name__ == "__main__":
    config = {}
    with open("config.json") as f:
        config = json.load(f)

    kernel = gcc_wrapper()
    try:
        kernel.build_and_save(config)
    except (Exception, SystemExit, KeyboardInterrupt) as e:
        os.unlink(f"kernel{kernel.pid}.soc")
        raise e

    os.unlink(f"kernel{kernel.pid}.soc")
