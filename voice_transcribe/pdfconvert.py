import csv
import datetime
import io
import json
import time
import traceback
import logging
import os
import requests
import re

from google.oauth2 import service_account
from google.api_core.exceptions import NotFound
from google.cloud import dlp
from google.cloud import language
#from google.cloud import pubsub, pubsub_v1
from google.cloud import storage
#from google.cloud.language import enums
#from google.cloud.language import types
from google.oauth2 import service_account
from google.cloud import vision


PROJECT_ID = 'mmvoice'
PDFBUCKET = 'gs://mmpdf1/'
#UPDATECRED = 'gs://mmvoice_creds/service-account2.json'
CREDFILE = 'mmkey.json'
#FILELIST = 'py1_gspathfiles.txt'
#FILES='py3_files.txt'


#Get Permissions needed for ML AI VOICE APIs
def gcs_credentials():
    scopes = [
        'https://www.googleapis.com/auth/devstorage.full_control',  # storage scope
        'https://www.googleapis.com/auth/pubsub',  # pub/sub scope
        'https://www.googleapis.com/auth/cloud-platform',  # speech-to-text scope
        'https://www.googleapis.com/auth/cloud-vision',
        'https://www.googleapis.com/auth/bigquery'  # BiqQuery
    ]
    service_account_file = 'mmkey.json'

    return service_account.Credentials.from_service_account_file(
        service_account_file, scopes=scopes)

gcs_credentials()


def async_detect_document(gcs_source_uri, gcs_destination_uri):
    """OCR with PDF/TIFF as source files on GCS"""
    from google.cloud import vision
    from google.cloud import storage
    from google.protobuf import json_format
    # Supported mime_types are: 'application/pdf' and 'image/tiff'
    mime_type = 'application/pdf'

    # How many pages should be grouped into each json output file.
    batch_size = 2

    client = vision.ImageAnnotatorClient()

    feature = vision.types.Feature(
        type=vision.enums.Feature.Type.DOCUMENT_TEXT_DETECTION)

    gcs_source = vision.types.GcsSource(uri=gcs_source_uri)
    input_config = vision.types.InputConfig(
        gcs_source=gcs_source, mime_type=mime_type)

    gcs_destination = vision.types.GcsDestination(uri=gcs_destination_uri)
    output_config = vision.types.OutputConfig(
        gcs_destination=gcs_destination, batch_size=batch_size)

    async_request = vision.types.AsyncAnnotateFileRequest(
        features=[feature], input_config=input_config,
        output_config=output_config)

    operation = client.async_batch_annotate_files(
        requests=[async_request])

    print('Waiting for the operation to finish.')
    operation.result(timeout=180)

    # Once the request has completed and the output has been
    # written to GCS, we can list all the output files.
    storage_client = storage.Client()

    match = re.match(r'gs://([^/]+)/(.+)', gcs_destination_uri)
    bucket_name = match.group(1)
    prefix = match.group(2)

    bucket = storage_client.get_bucket(bucket_name=bucket_name)

    # List objects with the given prefix.
    blob_list = list(bucket.list_blobs(prefix=prefix))
    print('Output files:')
    for blob in blob_list:
        print(blob.name)

    # Process the first output file from GCS.
    # Since we specified batch_size=2, the first response contains
    # the first two pages of the input file.
    output = blob_list[0]

    json_string = output.download_as_string()
    response = json_format.Parse(
        json_string, vision.types.AnnotateFileResponse())

    # The actual response for the first page of the input file.
    first_page_response = response.responses[0]
    annotation = first_page_response.full_text_annotation

    # Here we print the full text from the first page.
    # The response contains more information:
    # annotation/pages/blocks/paragraphs/words/symbols
    # including confidence scores and bounding boxes
    print(u'Full text:\n{}'.format(
        annotation.text))



source = 'gs://mmpdf1/Scan1.pdf'
destin = 'gs://mmpdfc/Scan1.txt'


async_detect_document(source,destin)

