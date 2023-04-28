
import os
from glob import glob
# import zipfile
import shutil
import nibabel as nib

import logging
log = logging.getLogger(__name__)

def rename_file(file_container, new_file_name):
    # new_sub_object = flywheel.models.Subject(label = target_sub_id)
    # fw.modify_subject(subject_id= fw_subject_id, body = new_sub_object)
    file_container.update(
            name=new_file_name
    )

def migrate_file(file_container, dest_proj_id):
    file_container.update({'project': dest_proj_id})

def fix_file_endings(file_path):
    file_name = os.path.basename(file_path)
    if file_name.split('.')[-1] != 'gz':
        print(f'RENAMING {file_path}')
        dest_path = file_path+'.gz'
        print(f'         {dest_path}')
        os.rename(file_path, dest_path)
        file_path = dest_path
        file_name = os.path.basename(file_path)
    if file_name.split('.')[-2] != 'nii':
        print(f'RENAMING {file_path}')
        prefix = file_name.split('.')[-2]
        this_path = os.path.dirname(file_path)
        dest_path = f'{this_path}/{prefix}.nii.gz'
        print(f'         {dest_path}')
        os.rename(file_path, dest_path)
        file_path = dest_path
        file_name = os.path.basename(file_path)
    return file_path,file_name

def get_new_file_name(file_name, sub_id, ses_label=[]):
    if ses_label==[]:
        ses_label = file_name.split('_')[1]
    seg_flag = 0
    if 't1ce' in file_name.lower():
        new_fname = f'{sub_id}_{ses_label}_T1CE_to_SRI.nii.gz'
    elif 't1' in file_name.lower():
        new_fname = f'{sub_id}_{ses_label}_T1_to_SRI.nii.gz'
    elif ('flair' in file_name.lower() or ('fl' in file_name.lower())):
        new_fname = f'{sub_id}_{ses_label}_FL_to_SRI.nii.gz'
    elif 't2' in file_name.lower():
        new_fname = f'{sub_id}_{ses_label}_T2_to_SRI.nii.gz'
    elif 'adc' in file_name.lower():
        new_fname = f'{sub_id}_{ses_label}_ADC_to_SRI.nii.gz'
    elif 'brainmask' in file_name.lower():
        new_fname = f'{sub_id}_{ses_label}_brainMask.nii.gz'
    elif ('manualseg' in file_name.lower()) \
            or ('manaulseg' in file_name.lower()) \
            or ('segmdm' in file_name.lower()):
        new_fname = f'{sub_id}_{ses_label}_ManualSegmentation.nii.gz'
        seg_flag=1
    else:
        log.info(f'>>> WARNING: skipping {file_name} does not match any expected file names: t1/t1ce/flair/t2/adc/brainmask/manualseg/segmdm. Please delete this file or update the file name as needed before processing.')
    return new_fname,ses_label,seg_flag

def fix_seg_labels(segm_path):
# convert labels to int format & check for values >= 5
# overwrites files
    segm = nib.load(segm_path)
    header_info = segm.header
    segm_data_before = segm.get_fdata()
    segm_data_after = segm_data_before.astype(int)
    wrong_label = segm_data_after[segm_data_after >= 5]
    if len(wrong_label) > 0:
        log.error(f'************** FOUND LABELS >= 5: {segm_path}')
    else:
        x = nib.Nifti1Image(segm_data_after, segm.affine, header_info)
        nib.save(x, segm_path)

def find_file_list(data_dir, sub_folder):
    file_list = glob(f'{data_dir}/{sub_folder}/*/*/*')
    if file_list==[]:
        file_list = glob(f'{data_dir}/{sub_folder}/*/*')
        if file_list==[]:
            file_list = glob(f'{data_dir}/{sub_folder}/*')
    out_list = []
    for file in file_list:
        if not os.path.isdir(file):
            out_list.append(file)
    return out_list

def fix_KF_ids(zip_path, sub_info, data_dir, not_proc_dir):
    sub_id = zip_path.split('/')[-1].rstrip('.zip')
    new_sub_id = []
    try:
        new_sub_id = sub_info[sub_info['kf_id']==sub_id]['cid'].tolist()[0]
        new_age = sub_info[sub_info['kf_id']==sub_id]['age'].astype(int).astype(str).tolist()[0]
    except:
        print(f'NO SUBJECT INFO FOUND FOR {sub_id}')
        shutil.move(zip_path, not_proc_dir)
        return [],0
    if new_sub_id:
        # change all of the file names
        unzip_file(zip_path, data_dir)
        file_list = find_file_list(data_dir, sub_id)
        for file_path in file_list:
            file_name = os.path.basename(file_path)
            this_path = os.path.dirname(file_path)
            if ('edit' in file_name) or \
                ('brainTumorMask' in file_name) or \
                ('_final' in file_name) or \
                ('pdf' in file_name):
                os.remove(file_path)
            else:
                new_fname,ses_label,seg_flag = get_new_file_name(file_name, new_sub_id, new_age)
                # make new directories to put renamed files in
                if not os.path.exists(f'{data_dir}/{new_sub_id}/'):
                    os.mkdir(f'{data_dir}/{new_sub_id}/')
                if not os.path.exists(f'{data_dir}/{new_sub_id}/{new_sub_id}/'):
                    os.mkdir(f'{data_dir}/{new_sub_id}/{new_sub_id}/')
                new_path = f'{data_dir}/{new_sub_id}/{new_sub_id}/{new_sub_id}_{ses_label}'
                if not os.path.exists(new_path):
                    os.mkdir(new_path)
                new_path = f'{new_path}/{new_fname}'
                os.rename(file_path, new_path)
        # re-zip for further processing
        old_dir_name = f'{data_dir}/{sub_id}'
        new_dir_name = f'{data_dir}/{new_sub_id}'
        shutil.make_archive(new_dir_name, 'zip', new_dir_name)
        shutil.rmtree(old_dir_name)
        os.remove(old_dir_name+'.zip')
        shutil.rmtree(new_dir_name)
        return new_dir_name+'.zip',1,new_sub_id,new_age

def upload_file_2_flywheel(fw, fw_group, target_proj_label, sub_id, ses_label, path_to_file):
    target_proj = fw.projects.find_first(f'label={target_proj_label}')
    # look to see if the container already exist in the Flywheel project
    # if not, then make a new empty container
    existing_files=[]
    this_file_name = os.path.basename(path_to_file)
    try:
        # if the acquisition already exists, check if there are any files in it
        target_acquisition = fw.lookup(f'{fw_group}/{target_proj_label}/{sub_id}/{ses_label}/processed')
        for file in target_acquisition.files:
            existing_files.append(file.name)
    except:
        try:
            target_session = fw.lookup(f'{fw_group}/{target_proj_label}/{sub_id}/{ses_label}')
        except:
            try:
                target_subject = fw.lookup(f'{fw_group}/{target_proj_label}/{sub_id}')
            except:
                target_subject = target_proj.add_subject({'label':sub_id})
            target_session = target_subject.add_session({'label':ses_label})
        target_acquisition = target_session.add_acquisition({'label':'processed'})
    if this_file_name not in existing_files:
        fw.upload_file_to_acquisition(target_acquisition.id, path_to_file)
