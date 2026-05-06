from preprocess import PreprocessADE, PreprocessModuleADE

if __name__ == "__main__":
    preprocess = [
        PreprocessADE(),
        PreprocessModuleADE()
    ]
    for process in preprocess:
        process.compute()
