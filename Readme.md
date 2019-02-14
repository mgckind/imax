### Cutouts image explorer

#### Simple deployment

Edit the config.yaml file to have the correct parameters

	   python3 server_aio.py

	   python3 client.py

#### Docker

1. Create an internal network

        docker network create --driver bridge cutouts

2. Start the server container and attach the volume with images, connect to network and expose port

	   docker run -it --name server -p 8888:8888 -v {PATH_TO_IMAGE}:{PATH_TO_IMAGES} --network cutouts cex sh

3. Start the client container, connect to network and expose the port

	   docker run -it --name client -p 8000:8000  --network cutouts cex sh

Now the containers can talk internally and names are dns resolved.
