# Copyright (C) 2013 Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
import errno
import subprocess
import fnmatch
import gzip
import tarfile
import pkgutil
import shutil
import re
import sys
from os.path import join

VALID = re.compile(r"[0-9]")

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def rm_f(filename):
    try:
        os.remove(filename)
    except OSError, e: # this would be "except OSError as e:" in python 3.x
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occured

def ln_sf(src, dst):
    try:
        os.symlink(src, dst)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(src):
            pass
        else: raise

class Transcription(object):
    
    def __init__(self, line, dirname):
        fileid, quote = line.split(' ', 1)
        quote = quote.strip("\n").replace("-", " ").lower()
        
        self.quote = quote
        self.filename = fileid.split("/")[-1]
        if not VALID.search(self.filename):
            raise Exception("Invalid PROMPTS line [%s] in dir [%s]" % (line.strip(), dirname))
        self.fileid = join(dirname, "mfc", self.filename)
        self._str = "<s> %s </s> (%s)" % (self.quote, self.filename)
    
    def __str__(self):
        return self._str
    
    def __lt__(self, other):
        assert isinstance(other, Transcription)
        return self._str < other._str 
        

class Train(object):

    def __init__(self, basedir, name = "voxforge_en_sphinx",
                 installed_dictionary = "/usr/share/pocketsphinx/model/lm/en_US/cmu07a.dic"):
        self.name = name
        self.basedir = basedir
        self.wavdir = join(self.basedir, "wav")
        self.etcdir = join(self.basedir, "etc")
        self.transcription = join(self.etcdir, "%s.transcription" % name)
        self.train_fileids = join(self.etcdir, "%s_train.fileids" % name)
        self.train_transcription = join(self.etcdir, "%s_train.transcription" % name)
        self.test_fileids = join(self.etcdir, "%s_test.fileids" % name)
        self.test_transcription = join(self.etcdir, "%s_test.transcription" % name)
        self.lm = join(self.etcdir, "%s.lm" % name)
        self.lm_dmp = join(self.etcdir, "%s.DMP" % self.lm)
        self.dictionary = join(self.etcdir, "%s.dic" % name)
        self.filler = join(self.etcdir, "%s.filler" % name)
        self.tree_questions = join(self.etcdir, "%s.tree_questions" % name)
        self.phone = join(self.etcdir, "%s.phone" % name)
        self.tgzdir = join(self.basedir, "www.repository.voxforge1.org")
        self.train_config = join(self.etcdir, "sphinx_train.cfg")
        
        self.installed_dictionary = installed_dictionary
        
        mkdir_p(self.basedir)
        mkdir_p(self.wavdir)
        mkdir_p(self.etcdir)

    def download(self):
        subprocess.check_call(["wget", "--mirror", "-P", self.basedir, "-A", "tgz", "-np",
            "http://www.repository.voxforge1.org/downloads/SpeechCorpus/Trunk/Audio/Main/16kHz_16bit"])

    def unpack(self):
        for root, dirnames, filenames in os.walk(self.tgzdir):
            for infile in fnmatch.filter(filenames, '*.tgz'):
                with tarfile.open(join(root, infile), mode='r') as tar:
                    tar.extractall(path = self.wavdir)

    def convert_flac(self):
        for root, dirnames, filenames in os.walk(self.wavdir):
            for flac in fnmatch.filter(dirnames, 'flac'):
                outdir = join(root, "wav")
                mkdir_p(outdir)

        for root, dirnames, filenames in os.walk(self.wavdir):
            for flac in fnmatch.filter(filenames, '*.flac'):
                infile = join(root, flac)
                outfile = infile.replace("flac", "wav")
                subprocess.check_call(["flac", "-f", "-s", "-d", infile, "-o", outfile])

    def link_mfc(self):
        for root, dirnames, filenames in os.walk(self.wavdir):
            for wav in fnmatch.filter(dirnames, 'wav'):
                outdir = join(root, "mfc")
                ln_sf("wav", outdir)

    def _collect_transcriptions(self):
        transcriptions = []
        for dirname in os.listdir(self.wavdir):
            prompt = join(self.wavdir, dirname, 'etc', 'PROMPTS')
            if os.path.isfile(prompt):
                with open(prompt, 'r') as contents:
                    for line in contents.readlines():
                        try:
                            transcriptions.append(Transcription(line, dirname))
                        except Exception, e:
                            print e
            else:
                print "Directory [%s] had no PROMPTS file, skipping" % dirname
        transcriptions.sort()
        return transcriptions

    def transcript(self):
        transcriptions = self._collect_transcriptions()
        
        # open all the files
        fd_transcription = open(self.transcription, 'w')
        fd_train_fileids = open(self.train_fileids, 'w')
        fd_train_transcription = open(self.train_transcription, 'w')
        fd_test_fileids = open(self.test_fileids, 'w')
        fd_test_transcription = open(self.test_transcription, 'w')
            
        try:
            for idx, transcription in enumerate(transcriptions):
                # make a complete transcription file just for building a decoder lm
                print >> fd_transcription, str(transcription)
                
                # use every tenth one for testing
                if (idx % 10) == 0:
                    print >> fd_test_fileids, transcription.fileid
                    print >> fd_test_transcription, str(transcription)
                else:
                    print >> fd_train_fileids, transcription.fileid
                    print >> fd_train_transcription, str(transcription)
            
        finally:
            fd_transcription.close()
            fd_train_fileids.close()
            fd_train_transcription.close()
            fd_test_fileids.close()
            fd_test_transcription.close()

    def build_lm(self):
        lm_gz = "%s.gz" % self.lm
        
        rm_f(self.lm)
        rm_f(lm_gz)
        rm_f(self.lm_dmp)
        
        subprocess.check_call(["/usr/bin/build-lm.sh", "-i", self.transcription, "-o", self.lm ],
                              env={"IRSTLM": "/usr"})
        
        with open(self.lm, "w") as fd:
            with gzip.open(lm_gz, 'rb') as fd_gzip:
                fd.write(fd_gzip.read())

        subprocess.check_call(["sphinx_lm_convert", "-i", self.lm, "-o", self.lm_dmp])

    def templates(self):
        with open(self.filler, 'w') as f:
            f.write(pkgutil.get_data("voxforgesphinxtrain", "template.filler"));
        with open(self.phone, 'w') as f:
            f.write(pkgutil.get_data("voxforgesphinxtrain", "template.phone"));
        with open(self.tree_questions, 'w') as f:
            f.write(pkgutil.get_data("voxforgesphinxtrain", "template.tree_questions"));
        shutil.copyfile(self.installed_dictionary, self.dictionary)
        subprocess.check_call(["patch", self.dictionary, join(os.path.dirname(sys.modules["voxforgesphinxtrain"].__file__), "dic.patch")])
        

    def setup(self):
        olddir = os.getcwd()
        try:
            os.chdir(self.basedir)
            subprocess.check_call(["sphinxtrain", "-t", self.name, "setup"])
        finally:
            os.chdir(olddir)

        with open(self.train_config, 'r') as f:
            config = f.readlines()
        
        with open(self.train_config, 'w') as f:    
            for line in config:
                #line = line.replace("$CFG_HMM_TYPE = '.cont.'", "$CFG_HMM_TYPE = '.semi.'"); # uncomment to train a semi-continuous model
                line = line.replace("$CFG_VECTOR_LENGTH = 13;", '''$CFG_VECTOR_LENGTH = 13;
$CFG_FEAT_WINDOW = 0;
''')
                line = line.replace("$CFG_VARNORM = 'no';", '''$CFG_VARNORM = 'no';
# (yes/no) Use letter-to-sound rules to guess pronunciations of
# unknown words (English, 40-phone specific)
$CFG_LTSOOV = 'no';
''')
                line = line.replace("$CFG_FINAL_NUM_DENSITIES = 8", "$CFG_FINAL_NUM_DENSITIES = 32")
                line = line.replace("$CFG_N_TIED_STATES = 200", "$CFG_N_TIED_STATES = 3000")
                line = line.replace("$CFG_NPART = 1", "$CFG_NPART = 20")
                line = line.replace("$CFG_NPART = 1", "$CFG_NPART = 20")
                line = line.replace("$CFG_LDA_MLLT = 'no'", "$CFG_LDA_MLLT = 'yes'")
                line = line.replace("$CFG_CONVERGENCE_RATIO = 0.1", "$CFG_CONVERGENCE_RATIO = 0.01")
                line = line.replace('$CFG_QUEUE_TYPE = "Queue"', '$CFG_QUEUE_TYPE = "Queue::POSIX"')
                line = line.replace('$CFG_MAKE_QUESTS = "yes"', '$CFG_MAKE_QUESTS = "no"')
                line = line.replace('$CFG_QUESTION_SET = "${CFG_BASE_DIR}/model_architecture/${CFG_EXPTNAME}.tree_questions";', '''if ($CFG_MAKE_QUESTS eq  'yes') {
  $CFG_QUESTION_SET = "${CFG_BASE_DIR}/model_architecture/${CFG_EXPTNAME}.tree_questions";
}
else {
  $CFG_QUESTION_SET = "${CFG_BASE_DIR}/etc/${CFG_EXPTNAME}.tree_questions";
}''')
                line = line.replace("$CFG_FORCEDALIGN = 'no'", "$CFG_FORCEDALIGN = 'yes'")
                line = line.replace('$CFG_FORCE_ALIGN_MODELDIR = "$CFG_MODEL_DIR/$CFG_EXPTNAME.falign_ci_$CFG_DIRLABEL";', '''
if ($CFG_FALIGN_CI_MGAU eq  'yes') {
  $CFG_FORCE_ALIGN_MODELDIR = "$CFG_MODEL_DIR/$CFG_EXPTNAME.falign_ci_${CFG_DIRLABEL}_$CFG_FINAL_NUM_DENSITIES";
}
else {
  $CFG_FORCE_ALIGN_MODELDIR = "$CFG_MODEL_DIR/$CFG_EXPTNAME.falign_ci_$CFG_DIRLABEL";
}
''')
                
#                line = line.replace("$DEC_CFG_SCRIPT = 'psdecode.pl'", "$DEC_CFG_SCRIPT = 's3decode.pl'")
            
                f.write(line) 
        
    def run(self):
        olddir = os.getcwd()
        try:
            os.chdir(self.basedir)
            subprocess.check_call(["sphinxtrain", "run"])
        finally:
            os.chdir(olddir)
    
    def clean(self):
        shutil.rmtree(join(self.basedir, "bwaccumdir"), ignore_errors=True)
        shutil.rmtree(join(self.basedir, "falignout"), ignore_errors=True)
        shutil.rmtree(join(self.basedir, "feat"), ignore_errors=True)
        shutil.rmtree(join(self.basedir, "model_architecture"), ignore_errors=True)
        shutil.rmtree(join(self.basedir, "model_parameters"), ignore_errors=True)
        shutil.rmtree(join(self.basedir, "qmanager"), ignore_errors=True)
        shutil.rmtree(join(self.basedir, "result"), ignore_errors=True)
        shutil.rmtree(join(self.basedir, "trees"), ignore_errors=True)
        rm_f(join(self.basedir, "voxforge_en_sphinx.html"))

	def configure(self):
	    self.unpack()
        self.convert_flac()
        self.link_mfc()
        self.transcript()
        self.build_lm()
        self.templates()
        self.setup()

	def do_all(self):
		self.clean()
        self.configure()
        self.run()

