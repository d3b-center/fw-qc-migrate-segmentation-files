"""Main module."""
import logging
import os
import pandas as pd

from fw_core_client import CoreClient
from flywheel_gear_toolkit import GearToolkitContext
import flywheel

from .run_level import get_analysis_run_level_and_hierarchy
from .migration_functions import *

log = logging.getLogger(__name__)

fw_context = flywheel.GearContext()
fw = fw_context.client

def run(client: CoreClient, gtk_context: GearToolkitContext):
    """Main entrypoint

    Args:
        client (CoreClient): Client to connect to API
        gtk_context (GearToolkitContext)
    """
    # get the Flywheel hierarchy for the run
    destination_id = gtk_context.destination["id"]
    hierarchy = get_analysis_run_level_and_hierarchy(gtk_context.client, destination_id)
    sub_label = hierarchy['subject_label']
    ses_label = hierarchy['session_label']
    project_label = hierarchy['project_label']
    group_name = hierarchy['group']

    # destination_proj = fw.projects.find_first(f'label=CBTN_completed_segmentations')
    destination_proj_id = '640108154977467819e18b7c' # CBTN_completed_segmentations

    # check subject ID is valid
    project_cntr = fw.projects.find_first(f'label={project_label}')
    if len(project_cntr.files)==0:
        log.error(f'>>> ERROR: no file cbtn_ids.csv attached to project!')
    else:
        for file_attachment in project_cntr.files:
            if file_attachment['name'] == 'cbtn_ids.csv':
                project_cntr.download_file('cbtn_ids.csv', 'cbtn_ids.csv')
                cbtn_ids = pd.read_csv('cbtn_ids.csv')
                cbtn_ids = cbtn_ids['CBTN Subject ID'].tolist()
    if cbtn_ids:
        if sub_label not in cbtn_ids:
            log.error(f'>>> ERROR: subject C-ID is not valid!')
        else:
            log.info(f'Step #1: subject label is a valid C-ID.')
    else:
        log.error(f'>>> ERROR: no file cbtn_ids.csv attached to project!')

    # now find files within this session
    ses = fw.lookup(f'{group_name}/{project_label}/{sub_label}/{ses_label}')
    ses = ses.reload()
    for acquisition in ses.aquisitions():
        log.info(f'Step #2: generating output file names.')
        for file in acquisition.files:
            file_name = file.name
            # ********** fix incorrect file endings
            file_path,file_name = fix_file_endings(file_path)
            # ********** fix incorrect file names by renaming all files accordingly
            # looks for strings in file names (t1, brainmask, manualseg/manaulseg/segmdm, etc.)
            new_fname,ses_label,seg_flag = get_new_file_name(file_name, sub_label, ses_label)
            # ********** convert all segmentation labels to INT and throw error if values >= 5
            if seg_flag==1:
                fix_seg_labels(file_path)
            # ********** rename the file with the new file name, or throw error
            rename_file(file, new_fname)
                # this_path = os.path.dirname(file_path)
                # new_path = f'{this_path}/{new_fname}'
            # ********** move the file to the destination project
            file = file.reload() # before was using fw.get_session(session_id)
            migrate_file(file, destination_proj_id)
            # if new_path not in processed_file_names:
            #     processed_file_names.append(new_path)
            #     os.rename(file_path, new_path)
            #     log.info(f'DONE: {new_fname}')
    # if there are no more files in the session, delete the session/subject in the source project

