from github import Github, ContentFile, Repository

def get_github_client(token: str = None) -> Github:
    """Create a GitHub client using the provided token."""
    if token: return Github(token)
    # Unauthenticated client if no token is provided
    return Github() 

def get_repo(github_client: Github, repo_name: str) -> Repository.Repository:
    """Get a GitHub repository by name."""
    try:
        return github_client.get_repo(repo_name)
    except Exception as e:
        raise ValueError(f"Could not find repository '{repo_name}': {e}")


def get_directory_content(repo: Repository.Repository, dir_path: str) -> dict[str, ContentFile.ContentFile]:
    """Get the content of the files in a specific directory of a GitHub repository."""
    file_data = {}
    contents = repo.get_contents(dir_path)
    while contents:
        file = contents.pop(0)
        if file.type == "dir":
            contents.extend(repo.get_contents(file.path))
        elif file.type == "file":
            try:
                file_data[file.name] = file
            except Exception as e:
                raise ValueError(f"Could not decode file content: {e}")
        else:
            print(file_data)

    return file_data

def get_file_content_from_directory(repo: Repository.Repository, directory_content: dict[str, ContentFile.ContentFile], file_name: str) -> str:
    """Get the content of a specific file in a directory of a GitHub repository."""
    if file_name not in directory_content:
        raise ValueError(f"File '{file_name}' not found in the directory content.")
    
    file = directory_content[file_name]
    if file.type != "file":
        raise ValueError(f"'{file_name}' is not a file.")
    
    try:
        return file.decoded_content.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Could not decode file content: {e}")


if __name__ == "__main__":
    repo = get_repo(get_github_client(), "prometheus-community/helm-charts")
    files = get_directory_content(repo, "charts/prometheus-kafka-exporter")

    import rich
    rich.print(get_file_content_from_directory(repo, files, "values.yaml"))
