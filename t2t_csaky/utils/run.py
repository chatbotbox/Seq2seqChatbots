import os
import datetime
import subprocess
import sys
import select

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# My imports.
from config import FLAGS, DATA_FILTERING
from data_filtering.hash_jaccard import HashJaccard
from data_filtering.encoder_state import EncoderState
from data_filtering.average_word_embedding import AverageWordEmbedding
from data_filtering.sentence_embedding import SentenceEmbedding
from data_filtering.identity_clustering import IdentityClustering
from data_filtering.distribution_loss import DistributionLoss
from data_filtering.unique_clustering import UniqueClustering


# Save the config.py file for a specific run.
def save_config_file(directory):
  # Make the data dir if it doesn't exist.
  if not os.path.exists(directory):
    os.makedirs(directory)

  # This will be used in the names of saved files.
  now = datetime.datetime.now()
  time_string = (str(now.year) + "." +
                 str(now.month) + "." +
                 str(now.day) + "." +
                 str(now.hour) + "." +
                 str(now.minute) + "." +
                 str(now.second))

  os.system("cp " + FLAGS["t2t_usr_dir"] + "/config.py " +
            directory + "/config." + time_string + ".txt")


# Initialize a data generation problem.
def data_generating():
  print("Program is running in data generation mode.")
  save_config_file(FLAGS["data_dir"])
  os.system("t2t-datagen \
               --t2t_usr_dir=" + FLAGS["t2t_usr_dir"] +
            " --data_dir=" + FLAGS["data_dir"] +
            " --problem=" + FLAGS["problem"])


# initialize a training loop with the given flags.
def training():
  print("Program is running in training mode.")
  save_config_file(FLAGS["train_dir"])

  # What hparams should we use.
  if FLAGS["hparams"] == "":
    hparam_string = "general_" + FLAGS["model"] + "_hparams"
  else:
    hparam_string = FLAGS["hparams"]

  os.system("t2t-trainer \
               --generate_data=False \
               --t2t_usr_dir=" + FLAGS["t2t_usr_dir"] +
            " --data_dir=" + FLAGS["data_dir"] +
            " --problem=" + FLAGS["problem"] +
            " --output_dir=" + FLAGS["train_dir"] +
            " --model=" + FLAGS["model"] +
            " --hparams_set=" + hparam_string +
            " --schedule=" + FLAGS["train_mode"] +
            " --worker_gpu_memory_fraction=" + str(FLAGS["memory_fraction"]) +
            " --keep_checkpoint_max=" + str(FLAGS["keep_checkpoints"]) +
            " --keep_checkpoint_every_n_hours=" +
            str(FLAGS["save_every_n_hour"]) +
            " --save_checkpoints_secs=" + str(FLAGS["save_every_n_secs"]) +
            " --train_steps=" + str(FLAGS["train_steps"]) +
            " --eval_steps=" + str(FLAGS["evaluation_steps"]) +
            " --local_eval_frequency=" + str(FLAGS["evaluation_freq"]))


# Intialize an inference test with the given flags.
def decoding():
  print("Program is running in inference/decoding mode.")
  save_config_file(FLAGS["decode_dir"])

  # What hparams should we use.
  if FLAGS["hparams"] == "":
    hparam_string = "general_" + FLAGS["model"] + "_hparams"
  else:
    hparam_string = FLAGS["hparams"]

  decode_mode_string = ""
  # Determine the decode mode flag.
  if FLAGS["decode_mode"] == "interactive":
    decode_mode_string = " --decode_interactive"
  elif FLAGS["decode_mode"] == "file":
    decode_mode_string = (" --decode_from_file=" +
                          FLAGS["decode_dir"] + "/" +
                          FLAGS["input_file_name"])

  os.system("t2t-decoder \
               --generate_data=False \
               --t2t_usr_dir=" + FLAGS["t2t_usr_dir"] +
            " --data_dir=" + FLAGS["data_dir"] +
            " --problem=" + FLAGS["problem"] +
            " --output_dir=" + FLAGS["train_dir"] +
            " --model=" + FLAGS["model"] +
            " --worker_gpu_memory_fraction=" + str(FLAGS["memory_fraction"]) +
            " --hparams_set=" + hparam_string +
            " --decode_to_file=" +
            FLAGS["decode_dir"] + "/" + FLAGS["output_file_name"] +
            ' --decode_hparams="beam_size=' + str(FLAGS["beam_size"]) +
            ",return_beams=" + FLAGS["return_beams"] +
            ",batch_size=" + str(FLAGS["batch_size"]) + '"' +
            decode_mode_string)


# Initialize a filtering problem.
def data_filtering():
  print("Program is running in data filtering mode.")
  save_config_file(DATA_FILTERING["data_dir"])

  filter_problems = {
      "hash_jaccard": HashJaccard,
      "sentence_embedding": SentenceEmbedding,
      "rnn_state": EncoderState,
      "identity_clustering": IdentityClustering,
      "avg_embedding": AverageWordEmbedding,
      "unique_avg_embedding": UniqueClustering,
      "distribution_loss": DistributionLoss
  }

  problem = filter_problems[DATA_FILTERING["filter_problem"]]("full")
  problem.run()


# Run a longer experiment, with many calls to the above functions.
def experiment():
  # overwrite the checkpoint file
  ckpt_list = [71275, 41302, 49000, 69676, 64000, 68000, 66865, 63500, 68764, 65500]
  dir_list = ["base_with_numbers", "base_both_identity_clustering", "base_source_based_identity_clustering_CORRECT", "base_target_based_identity_clustering",
              "base_both_avg_embedding", "base_target_based_avg_embedding", "base_source_based_avg_embedding",
              "base_both_sent_eval", "base_target_based_sent_eval", "base_source_based_sent_eval"]
  for ckpt, folder in zip(ckpt_list, dir_list):
    FLAGS["data_dir"] = "data_dir/DailyDialog/" + folder
    FLAGS["train_dir"] = "train_dir/DailyDialog/trf_20_dropout-" + folder
    FLAGS["decode_dir"] = "decode_dir/DailyDialog/trf_20_dropout-" + folder
    with open(FLAGS["train_dir"] + "/checkpoint", "w") as ckpt_file:
      ckpt_file.write('model_checkpoint_path: "model.ckpt-' + str(ckpt) + '"')
    FLAGS["output_file_name"] = "test_set_" + str(ckpt) + ".txt"
    decoding()


# Run some command line stuff, and get the output in real-time.
def run_command(command=["t2t-datagen",
                         "--t2t_usr_dir=" + FLAGS["t2t_usr_dir"],
                         "--data_dir=" + FLAGS["data_dir"],
                         "--problem=" + FLAGS["problem"]]):
  """
  Param:
    :command: List containing the command-line arguments.
  """
  process = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
  while True:
    reads = [process.stdout.fileno(), process.stderr.fileno()]
    ret = select.select(reads, [], [])

    for fd in ret[0]:
      if fd == process.stdout.fileno():
        read = process.stdout.read(1)
        sys.stdout.write(read.decode("utf-8"))
        sys.stdout.flush()
      if fd == process.stderr.fileno():
        read = process.stderr.read(1)
        sys.stderr.write(read.decode("utf-8"))
        sys.stdout.flush()

    if not read:
      break
