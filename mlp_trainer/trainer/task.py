import argparse
import logging
import os
import json

import tensorflow as tf
import trainer.model as model

import hypertune


def train_and_evaluate(args):
    """
    TODO: description
    :param args:
    :return:
    """

    # choose optimizer from input arguments
    if args.optimizer.lower() == 'adam':
        optimizer = tf.keras.optimizers.Adam
    elif args.optimizer.lower() == 'nadam':
        optimizer = tf.keras.optimizers.Nadam
    elif args.optimizer.lower() == 'rmsprop':
        optimizer = tf.keras.optimizers.RMSprop
    elif args.optimizer.lower() == 'sgd':
        optimizer = tf.keras.optimizers.SGD
    else:
        optimizer = None

    # format parameters from input arguments
    params = {
        'dense_neurons_1': args.dense_neurons_1,
        'dense_neurons_2': args.dense_neurons_2,
        'dense_neurons_3': args.dense_neurons_3,
        'activation': args.activation,
        'dropout_rate_1': args.dropout_rate_1,
        'dropout_rate_2': args.dropout_rate_2,
        'dropout_rate_3': args.dropout_rate_3,
        'optimizer': optimizer,
        'learning_rate': args.learning_rate,
        'chunk_size': args.chunk_size,
        'batch_size': args.batch_size,
        'epochs': args.epochs,
        'validation_freq': args.validation_freq,
        'kernel_initial_1': args.kernel_initial_1,
        'kernel_initial_2': args.kernel_initial_2,
        'kernel_initial_3': args.kernel_initial_3
    }

    """Parse TF_CONFIG to cluster_spec and call run() method.

    TF_CONFIG environment variable is available when running using
    gcloud either locally or on cloud. It has all the information required
    to create a ClusterSpec which is important for running distributed code.

    Args:
        args (args): Input arguments.
    """

    tf_config = os.environ.get('TF_CONFIG')
    print(tf_config)
    # If TF_CONFIG is not available run local.
    if tf_config:
        tf_config_json = json.loads(tf_config)
        cluster = tf_config_json.get('cluster')
        job_name = tf_config_json.get('task', {}).get('type')
        task_index = tf_config_json.get('task', {}).get('index')

        tf_config_json["cluster"]["chief"] = cluster.get("master")
        if cluster.get("master"):
            del tf_config_json["cluster"]["master"]

        # Map ML Engine master to chief for TF
        if job_name == "master":
            tf_config_json["task"]["type"] = "chief"
            os.environ['TF_CONFIG'] = json.dumps(tf_config_json)

    tf.config.optimizer.set_jit(True)

    # train model and get history
    history, mlp_model = model.train_mlp_batches(
        args.table_id,
        params=params
    )

    # save model and history to job directory
    model.save_model(
        mlp_model,
        job_dir=args.job_dir
    )


def tune(args):

    logging.info('In tuning procedure...')

    # choose optimizer from input arguments
    if args.optimizer.lower() == 'adam':
        optimizer = tf.keras.optimizers.Adam
    elif args.optimizer.lower() == 'nadam':
        optimizer = tf.keras.optimizers.Nadam
    elif args.optimizer.lower() == 'rmsprop':
        optimizer = tf.keras.optimizers.RMSprop
    elif args.optimizer.lower() == 'sgd':
        optimizer = tf.keras.optimizers.SGD
    else:
        optimizer = None

    # format parameters from input arguments
    params = {
        'dense_neurons_1': args.dense_neurons_1,
        'dense_neurons_2': args.dense_neurons_2,
        'dense_neurons_3': args.dense_neurons_3,
        'activation': args.activation,
        'dropout_rate_1': args.dropout_rate_1,
        'dropout_rate_2': args.dropout_rate_2,
        'dropout_rate_3': args.dropout_rate_3,
        'optimizer': optimizer,
        'learning_rate': args.learning_rate,
        'chunk_size': args.chunk_size,
        'batch_size': args.batch_size,
        'epochs': args.epochs,
        'validation_freq': args.validation_freq,
        'kernel_initial_1': args.kernel_initial_1,
        'kernel_initial_2': args.kernel_initial_2,
        'kernel_initial_3': args.kernel_initial_3
    }

    # train model and get history
    history, mlp_model = model.train_mlp_batches(
        args.table_id,
        params=params
    )

    logging.info(history.history)

    hpt = hypertune.HyperTune()
    hpt.report_hyperparameter_tuning_metric(
        hyperparameter_metric_tag='loss',
        metric_value=float(history.history['loss'][0]),
        global_step=100)

    logging.info('Reported HP metric...')


if __name__ == '__main__':

    # TODO: update argument defaults with hp tuning results

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--table-id',
        type=str,
        help='BigQuery table containing dataset',
        default='finaltaxi_encoded_sampled_small')
    parser.add_argument(
        '--task',
        type=str,
        help='train or tune',
        default='train')
    parser.add_argument(
        '--job-dir',
        type=str,
        help='Directory to create in bucket to write history and export model',
        default='test_job_dir')
    parser.add_argument(
        '--dense-neurons-1',
        type=int,
        help='Number of neurons in first model layer, default=64',
        default=64)
    parser.add_argument(
        '--dense-neurons-2',
        type=int,
        help='Number of neurons in second model layer, default=32',
        default=32)
    parser.add_argument(
        '--dense-neurons-3',
        type=int,
        help='Number of neurons in third model layer, default=8',
        default=8)
    parser.add_argument(
        '--activation',
        type=str,
        help='Activation function, default=relu',
        default='relu')
    parser.add_argument(
        '--dropout-rate-1',
        type=float,
        help='Dropout rate for first model layer, default=0.1',
        default=0.1)
    parser.add_argument(
        '--dropout-rate-2',
        type=float,
        help='Dropout rate for second model layer, default=0.1',
        default=0.1)
    parser.add_argument(
        '--dropout-rate-3',
        type=float,
        help='Dropout rate for third model layer, default=0.1',
        default=0.1)
    parser.add_argument(
        '--optimizer',
        type=str,
        help='Optimizer function, default=adam',
        default='adam')
    parser.add_argument(
        '--learning-rate',
        type=float,
        help='Learning rate, default=0.1',
        default=0.1)
    parser.add_argument(
        '--batch-size',
        type=int,
        help='Batch size, default=64',
        default=64)
    parser.add_argument(
        '--chunk-size',
        type=int,
        help='Chunk size to load training data, default=200000',
        default=200000)
    parser.add_argument(
        '--epochs',
        type=int,
        help='Number of epochs to train, default=3',
        default=3)
    parser.add_argument(
        '--validation-freq',
        type=int,
        help='Validation frequency, default=5',
        default=1)
    parser.add_argument(
        '--kernel-initial-1',
        type=str,
        help='Kernel initializer for first model layer, default=normal',
        default='normal')
    parser.add_argument(
        '--kernel-initial-2',
        type=str,
        help='Kernel initializer for second model layer, default=normal',
        default='normal')
    parser.add_argument(
        '--kernel-initial-3',
        type=str,
        help='Kernel initializer for third model layer, default=normal',
        default='normal')
    args, _ = parser.parse_known_args()

    if args.task in 'train':
        train_and_evaluate(args)
    elif args.task in 'tune':
        tune(args)
    else:
        logging.error('--task must be \'train\' or \'tune\'')
