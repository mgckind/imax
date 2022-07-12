# IMAX: Interactive Multi-image Analysis eXplorer

This is an interactive tool for visualize and classify multiple images at a time. It written in Python and Javascript. It is based on [Leaflet](https://leafletjs.com/) and it reads the images from a single directory and there is no need for multiple resolutions folders as images are scaled dynamically when zooming in/out. It runs an asyncio server in the back end and supports up 10,000 images reasonable well. It can load more images but it will slower. It runs using multiple cores and has been tested with over 50K images.

You can move and label images all from the keyboard.

You can see a (not very good) gif demo ot the tool in action, or a better video is [here](https://vimeo.com/319571639)

![Demo](demo/demo.gif)

### Deployment

#### Simple deployment

Create Conda Environment:

    conda create -n imax python=3
    conda activate imax
  
Install Cairo Library

    conda install -c conda-forge cairosvg

Clone this repository:

		git clone https://github.com/mgckind/imax.git
		cd imax/
    pip install -r requirements.txt

Create a config file template:

		./imax-run create-config

Edit the `config.yaml` file to have the correct parameters, see [Configuration](#Configuration) for more info.

Create fake images to test, 

    ./imax-run create-fake-images -n 1200 -f images -m inferno



Start the server:

	   ./imax-run server

Start the client and visit the url printed python_server:

	   ./imax-run client

If you are running locally you can go to [http://localhost:8000/](http://localhost:8000/)

#### Docker (Needs revision)

0. Create image from Dockerfile

        cd imax
        docker build -t imax .

1. Create an internal network so server/client can talk through the internal network (is not need for now as we are exposing both services at the localhost)

        docker network create --driver bridge imaxnet

2. Create local config file to be mounted inside the containers. Create `config.yaml` based on the template, and replace the image location.

3. Start the server container and attach the volume with images, connect to network and expose port 8888 to localhost

           docker run -d --name server -p 8888:8888 -v {PATH TO CONFIG FILE}:/home/explorer/server/config.yaml -v {PATH TO LOCAL IMAGES}:{PATH TO CONTAINER IMAGES} --network imaxnet imax python server.py

4. Start the client container, connect to network and expose the port 8000 to local host

           docker run -d --name client -p 8000:8000 -v {PATH TO CONFIG FILE}:/home/explorer/server/config.yaml  --network imaxnet imax python client.py

Now the containers can talk at the localhost. 
If you are running locally you can go to [http://localhost:8000/](http://localhost:8000/)


### Usage

This is the Help window displayed


----

<h3>Help</h3> <hr><span><img src="icons/fa-square-o.png"/> -&gt; Fullscreen</span> <br><span><img src="icons/fa-star-half-o.png"/> -&gt; Invert colors</span> <br><span><img src="icons/fa-eye.png"/>/<img src="icons/fa-eye-slash.png"/> -&gt; Toggle On/Off classified tiles. <br>First time it reads from DB.</span> <br> <span><img src="icons/fa-random.png"/> -&gt; Random. Show a new random subsample (if available data is larger)</span> <br><span><img src="icons/fa-filter.png"/> -&gt; Apply filter to the displayed data.</span> <br> Use the checkboxes on the left bottom side. -1 means no classified. <br><span><img src="icons/fa-refresh.png"/> -&gt; Reset filters and view. Do not display deleted images.</span> <br> <hr><p> Move around with mouse and keyboard , use the mouse wheel to zoom in/out and double click to focus on one image.</p><h4> Keyboard </h4>Use "w","a","s","d" to move the selected tile and the keyboard numbers to apply a class as defined in the configuration file <br>Use "+", "-" to zoom in/out <br> Use "c" to clear any class selection <br> Use "t" to toggle on/off the classes <br>Use "h" to toggle on/off the Help<br> Use "f" to toggle on/off Full screen <br>Defined classes will appear at the bottom right side of the map

----

### Configuration

This is the template config file to use:

```
#### DATABASE
db:
  dbpath: '{FILL ME}' # Path to sqlite files
  merge: false
#### DISPLAY
display:
  path: '{FILL ME}' # Path to images
  nimages: 1200 #Number of objects to be displayed even if there are more in the folder
  xdim: 40 #X dimension for the display
  ydim: 30 #Y dimension for the display
  tileSize: 256 #Size of the tile for which images are resized at max zoom level
  minXrange: 0
  minYrange: 0
  deltaZoom: 5 #default == 5
  min-width: 500
  max-width: 1400
  min-height: 500
  max-height: 1000
#### SERVER
server:
  ssl: false #use ssl, need to have certificates
  sslName: test #prefix of .crt and .key files inside ssl/ folder e.g., ssl/{sslName.key}
  host: 'http://localhost' #if using ssl, change to https
  port: 8888
  rootUrl: '/' #root url for server, e.g. request are made to /cexp/, if None use "/"
  #workers: None # None will default to the workers in the machine
#### CLIENT
client:
  host: 'http://localhost'
  port: 8000
#### OPERATIONS options
operation:
  updates: false #allows to update and/or remove classes to images, false and classes are fixed.
  help: true
  fullscreen: true
  invert: true
  toggle-classes: true
  random: true
  filter: true
  reset: true
  search: true
#### CLASSES
#### classes, use any classes from 0 to 9, class 0 is for hidden! class -1 is no class
classes:
    - Test: 5
```
