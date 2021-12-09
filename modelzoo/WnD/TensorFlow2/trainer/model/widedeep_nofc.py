# Copyright (c) 2021, NVIDIA CORPORATION. All rights reserved.
# Modifications copyright Intel
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tensorflow as tf


def wide_deep_model(args, features):
    NUMERIC_COLUMNS = features.numerical_keys
    CATEGORICAL_COLUMNS = features.categorical_keys
    categorical_meta = features.categorical_meta

    wide_weighted_outputs = []
    deep_embedding_outputs = []
    numeric_dense_inputs = []
    features = {}

    for col in NUMERIC_COLUMNS+CATEGORICAL_COLUMNS:
        features[col] = tf.keras.Input(shape=(1,),
                                           batch_size=None,
                                           name=col,
                                           dtype=tf.float32 if col in NUMERIC_COLUMNS else tf.int32,
                                           sparse=False)

    for key in CATEGORICAL_COLUMNS:
        wide_weighted_outputs.append(tf.keras.layers.Flatten()(tf.keras.layers.Embedding(
            categorical_meta[key]['voc_size'], 1, input_length=1)(features[key])))
        deep_embedding_outputs.append(tf.keras.layers.Flatten()(tf.keras.layers.Embedding(
            categorical_meta[key]['voc_size'], categorical_meta[key]['emb_dim'])(features[key])))
    for key in NUMERIC_COLUMNS:
        numeric_dense_inputs.append(features[key])

    categorical_output_contrib = tf.keras.layers.add(wide_weighted_outputs,
                                                     name='categorical_output')
    numeric_dense_tensor = tf.keras.layers.concatenate(
        numeric_dense_inputs, name='numeric_dense')

    dnn = tf.keras.layers.concatenate(numeric_dense_inputs+deep_embedding_outputs)
    for unit_size in args.deep_hidden_units:
        dnn = tf.keras.layers.Dense(units=unit_size, activation='relu')(dnn)
        dnn = tf.keras.layers.Dropout(rate=args.deep_dropout)(dnn)
        dnn = tf.keras.layers.BatchNormalization()(dnn)
    dnn = tf.keras.layers.Dense(units=1)(dnn)
    dnn_model = tf.keras.Model(inputs=features,
                               outputs=dnn)
    linear_output = categorical_output_contrib + tf.keras.layers.Dense(1)(numeric_dense_tensor)

    linear_model = tf.keras.Model(inputs=features,
                                  outputs=linear_output)

    model = tf.keras.experimental.WideDeepModel(
        linear_model, dnn_model, activation='sigmoid')

    return model