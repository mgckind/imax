### Cutouts image explorer

This is an interactive tool for visualize and classify multiple images at a time. It written in Python and Javascript. It is based on [Leaflet](https://leafletjs.com/) and it reads the images from a single directory (there is no need for multiple resolutions as images are scaled dynamically). It running asyncio server in the back end and support up 10,000 images reasonable well. I can load more images but it will slower.

You can move and label images all from the keyboard.

### Deployment

#### Simple deployment

Clone this repository:

		git clone https://github.com/mgckind/cutouts-explorer.git
		cd cutouts-explorer/python_server

Create a config file template:

		cp config_template.yaml config.yaml

Edit the `config.yaml` file to have the correct parameters, see [Configuration](Readme.md#Configuration) for more info.

Start the server:

	   python3 server_aio.py

Start the client and visit the url printed python_server:

	   python3 client.py


#### Docker

1. Create an internal network

        docker network create --driver bridge cutouts

2. Start the server container and attach the volume with images, connect to network and expose port

	   docker run -it --name server -p 8888:8888 -v {PATH_TO_IMAGE}:{PATH_TO_IMAGES} --network cutouts cex sh

3. Start the client container, connect to network and expose the port

	   docker run -it --name client -p 8000:8000  --network cutouts cex sh

Now the containers can talk internally and names are dns resolved.

### Usage

### Configuration
