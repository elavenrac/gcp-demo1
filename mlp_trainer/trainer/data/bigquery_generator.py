import math
import pickle
import codecs
from typing import Tuple, Iterator

import tensorflow as tf

from trainer.data import bigquery as data
from trainer.data import features as features


def bq_stream_generator(table_id: bytes, partition: bytes):
    session = data.get_data_partition_sharded(table_id.decode("utf-8"), partition.decode("utf-8"), shards=100)
    encoded_session = codecs.encode(pickle.dumps(session), "base64")
    for stream in session.streams:
        tf.get_logger().info("Adding BigQuery read session %s to dataset" % (stream.name))
        yield(tf.constant(encoded_session), tf.constant(stream.name))


def get_reader_for_stream(session_pickled: bytes, stream_name_bytes: bytes):
    session = pickle.loads(codecs.decode(session_pickled, "base64"))
    stream_name = stream_name_bytes.decode("utf-8")
    for stream in session.streams:
        if stream.name == stream_name:
            tf.get_logger().info("Reading from BigQuery read session %s" % (stream.name))
            reader = data.get_reader(data.client, stream)
            rows = reader.rows(session)
            for row in rows:
                # features_dict = {}
                # for feat in features.defs():
                #     features_dict[feat.get("name")] = tf.constant(row.get(feat.get("name")))
                
                cols = []
                # add feature columns 
                for feat in features.defs():
                    cols.append(row.get(feat.get("name")))
                # add label
                cols.append(row.get("cash"))

                yield tuple(cols)


@tf.function
def get_data(table_id: str, partition: str, batch_size: int,
             epochs: int, chunk_size: int, cycle_length: int,
             num_workers: int, task_index: int, map_function='keras') -> tf.data.Dataset:
    if map_function == 'keras':
        map_fn = keras_map_fn
    elif map_function == 'estimator':
        map_fn = estimator_map_fn

    # session = data.get_data_partition_sharded(table_id, partition, shards=100)
    # encoded_session = codecs.encode(pickle.dumps(session), "base64")
    # streams = []
    # sessions = []
    # for stream in session.streams:
    #     sessions.append(tf.constant(encoded_session))
    #     streams.append(tf.constant(stream.name))

    # tf.get_logger().info("Bigquery Storage API created {} streams. Will be sharded among {} workers".format(len(streams), num_workers))
 
    # dataset = tf.data.Dataset.from_tensor_slices(
    #     (sessions,
    #     streams)
    # ).

    streams_ds = tf.data.Dataset.from_generator(
        bq_stream_generator,
        (tf.string, tf.string),
        output_shapes=(tf.TensorShape([]), tf.TensorShape([])),
        args=(table_id, partition)
    ).shard(
        num_workers,
        task_index
    )
    
    elements_ds = streams_ds.interleave(
        lambda session, stream:
        tf.data.Dataset.from_generator(
            get_reader_for_stream,
            tuple(features.get_generator_output()),
            output_shapes=tuple(features.get_generator_output_shape()),
            args=(session, stream)
        ).shard(
            num_workers,
            task_index
        ).prefetch(
            buffer_size=batch_size*5
        ).shuffle(
            buffer_size=batch_size*5
        ),
        num_parallel_calls=tf.data.experimental.AUTOTUNE,
        cycle_length=cycle_length,
        # block_length=batch_size,
    ).interleave(
        map_fn,
        num_parallel_calls=tf.data.experimental.AUTOTUNE,
        cycle_length=cycle_length
    ).batch(
        batch_size
    ).prefetch(
        math.ceil((batch_size*5) / batch_size)
    ).repeat(epochs)

    return elements_ds


@tf.function
def estimator_map_fn(*args):
    feats = features.defs()
    feat_cols = {}
    i = 0
    # Loop over feat cols. Label is last and we'll manually add
    # This is ugly bc it depends on everything staying in order
    while i < len(args) - 1:
        feat_cols[feats[i].get('name')] = args[1]
        i += 1
    
    return tf.data.Dataset.from_tensors(
        ((feat_cols), args[len(args)-1], (None, 1))
    )



@tf.function
def keras_map_fn(*args):
    feat_cols = []
    i = 0
    # Loop over feat cols. Label is last and we'll manually add
    while i < len(args) - 1:
        feat_cols.append(args[i])
        i += 1
    
    return tf.data.Dataset.from_tensors(
        (
            tf.convert_to_tensor(tuple(feat_cols), dtype=tf.dtypes.float32), 
            # tf.constant(args[len(args)-1], dtype=tf.dtypes.float32, shape=tf.TensorShape([None, 1]))
            tf.convert_to_tensor([args[len(args)-1]])
        )
    )
