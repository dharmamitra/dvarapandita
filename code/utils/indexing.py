def create_filelist(main_path,bucket_path):
    filelist =  glob.glob(filepath + '/**/*.p', recursive=True)
    return_list = []
    for current_file in filelist:
        #print(current_file)
        if not os.path.isfile(current_file.replace(".p","_results.npy.gz").replace(main_path,bucket_path)):
            return_list.append(current_file)
    return return_list
