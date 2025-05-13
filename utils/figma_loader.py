import requests
from langchain_community.document_loaders.figma import FigmaFileLoader


def download_figma_image(figma_file_id: str, node_id: str, figma_token: str, format="png"):
    """
    Download a Figma node as an image.

    :param figma_file_id: The ID of the Figma file.
    :param node_id: The ID of the Figma node to download.
    :param figma_token: The Figma API token.
    :param format: The image format (png, jpg, svg, pdf).
    """
    url = f"https://api.figma.com/v1/images/{figma_file_id}?ids={node_id}&format={format}"
    headers = {"X-Figma-Token": figma_token}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        image_url = response.json().get("images", {}).get(node_id.replace("-",":"))
        if image_url:
            image_response = requests.get(image_url)
            with open(f"figma_node_{node_id}.{format}", "wb") as f:
                f.write(image_response.content)
            print(f"Image figma_node_{node_id}.{format} downloaded successfully!")
        else:
            print("No image URL found.")
    else:
        print(f"Error: {response.status_code}, {response.text}")


def load_figma_file(figma_file_id: str, figma_token: str, node_id: str):
    """
    Load a Figma file.

    :param figma_file_id: The ID of the Figma file.
    :param figma_token: The Figma API token.
    :param node_id: The ID of the Figma node to load.
    """
    loader = FigmaFileLoader(figma_token, node_id,figma_file_id )
    documents = loader.load()

    for document in documents:
        print(document)


if __name__ == '__main__':
    pass