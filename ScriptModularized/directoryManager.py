import os

class DirectoryManager:
    def __init__(self, output_folder_name, input_folder, replace_folder=True):
        # Get the current working directory and assign it to 'scripts_data_folder'
        self.output_folder_name = output_folder_name
        self.input_folder = input_folder

        # if output folder name already exists and replace_folder is True, remove it
        if os.path.exists(self.output_folder_name) and replace_folder:
            os.rmdir(self.output_folder_name)
        if os.path.exists(self.output_folder_name) and not replace_folder:
            raise Exception("Output folder already exists!") 

        self.output_folder = os.path.join(self.output_folder_name)
        # create directory
        os.makedirs(self.output_folder)

