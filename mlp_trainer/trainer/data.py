from typing import List, Tuple
from google.cloud import bigquery_storage_v1beta1


def get_table_ref(table_id: str) -> bigquery_storage_v1beta1.types.TableReference:
    """Sets up the table spec configuration

    @TODO: Should parameterize
    """
    table_ref = bigquery_storage_v1beta1.types.TableReference()
    table_ref.project_id = "ml-sandbox-1-191918"
    table_ref.dataset_id = "chicagotaxi"
    table_ref.table_id = table_id
    return table_ref


def get_read_options(partition_name=None):
    """Selects the columns from the  table. Ordering here doesn't matter.
    Bigquery will return columns in the order they appear in the schema."""
    read_options = bigquery_storage_v1beta1.types.TableReadOptions()
    read_options.selected_fields.append("cash")
    read_options.selected_fields.append("year")
    read_options.selected_fields.append("start_time_norm_midnight")
    read_options.selected_fields.append("start_time_norm_noon")
    read_options.selected_fields.append("pickup_long_std")
    read_options.selected_fields.append("pickup_long_std")
    read_options.selected_fields.append("pickup_lat_centered")
    read_options.selected_fields.append("pickup_long_centered")
    read_options.selected_fields.append("day_of_week_MONDAY")
    read_options.selected_fields.append("day_of_week_TUESDAY")
    read_options.selected_fields.append("day_of_week_WEDNESDAY")
    read_options.selected_fields.append("day_of_week_THURSDAY")
    read_options.selected_fields.append("day_of_week_FRIDAY")
    read_options.selected_fields.append("day_of_week_SATURDAY")
    read_options.selected_fields.append("day_of_week_SUNDAY")
    read_options.selected_fields.append("month_JANUARY")
    read_options.selected_fields.append("month_FEBRUARY")
    read_options.selected_fields.append("month_MARCH")
    read_options.selected_fields.append("month_APRIL")
    read_options.selected_fields.append("month_MAY")
    read_options.selected_fields.append("month_JUNE")
    read_options.selected_fields.append("month_JULY")
    read_options.selected_fields.append("month_AUGUST")
    read_options.selected_fields.append("month_SEPTEMBER")
    read_options.selected_fields.append("month_OCTOBER")
    read_options.selected_fields.append("month_NOVEMBER")
    read_options.selected_fields.append("month_DECEMBER")

    if partition_name:
        read_options.row_restriction = 'ml_partition = "{}"'.format(partition_name)    
    return read_options


def get_session(client: bigquery_storage_v1beta1.BigQueryStorageClient,
                table_ref: bigquery_storage_v1beta1.types.TableReference,
                read_options: bigquery_storage_v1beta1.types.TableReadOptions,
                parent: str,
                streams: int) -> bigquery_storage_v1beta1.types.ReadSession:
    return client.create_read_session(
        table_ref,
        parent,
        table_modifiers=None,
        read_options=read_options,
        # This API can also deliver data serialized in Apache Arrow format.
        # This example leverages Apache Avro.
        format_=bigquery_storage_v1beta1.enums.DataFormat.AVRO,
        requested_streams=streams,
        # We use a LIQUID strategy in this example because we only read from a
        # single stream. Consider BALANCED if you're consuming multiple streams
        # concurrently and want more consistent stream sizes.
        sharding_strategy=(bigquery_storage_v1beta1.enums.ShardingStrategy.BALANCED),
    )


def get_reader(client: bigquery_storage_v1beta1.BigQueryStorageClient,
               stream: bigquery_storage_v1beta1.types.Stream) -> bigquery_storage_v1beta1.reader.ReadRowsStream:
    return client.read_rows(bigquery_storage_v1beta1.types.StreamPosition(stream=stream), timeout=10000)


def get_data_partition_sharded(table_id: str, partition_name: str, shards=1) -> Tuple[bigquery_storage_v1beta1.types.ReadSession, List[bigquery_storage_v1beta1.types.ReadSession]]:
    client = bigquery_storage_v1beta1.BigQueryStorageClient()
    tableref = get_table_ref(table_id)
    session = get_session(client,
                          tableref,
                          get_read_options(partition_name),
                          "projects/{}".format(tableref.project_id),
                          shards)
    readers = []
    for stream in session.streams:
        reader = get_reader(client, stream)
        readers.append(reader)

    return session, readers


def get_df(reader, session):
    """Returns a Pandas DataFrame from a configured reader and session"""
    rows = reader.rows(session)
    return rows.to_dataframe()


def get_data(table_id, partition_name=None):
    """Get prepared taxi ride data for training

    Args:
        partition_name (str):
            Optional partition name to add as restriction
    Returns:
        pandas.DataFrame: Pandas DataFrame
    """
    client = bigquery_storage_v1beta1.BigQueryStorageClient()
    session = get_session(client, get_table_ref(table_id), get_read_options(partition_name), "projects/{}".format(get_table_ref(table_id).project_id), streams=1)
    reader = get_reader(client, session)
    df = get_df(reader, session)
    return df


def get_reader_rows(table_id, partition_name=None):
    """
    TODO: description
    :param table_id:
    :param partition_name:
    :return:
    """
    client = bigquery_storage_v1beta1.BigQueryStorageClient()
    session = get_session(
        client,
        get_table_ref(table_id),
        get_read_options(partition_name),
        "projects/{}".format(get_table_ref(table_id).project_id),
        streams=1
    )
    reader = get_reader(client, session)
    rows = reader.rows(session)

    return rows
