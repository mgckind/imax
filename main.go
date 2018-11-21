package main

import (
	"bytes"
	"flag"
	"image"
	"image/color"
	"image/draw"
	"image/jpeg"
	"image/png"
	"log"
	"net/http"
	"strconv"

	"fmt"
	"path/filepath"
	"os"
	"math"

	"github.com/nfnt/resize"
)

var root = flag.String("root", ".", "file system path")
var TILESIZE int
var NTILES int
var idx [][]int
var images []string
var err error

func main() {
	images, err = filepath.Glob("cutouts/*.png")
	if err != nil {
		fmt.Print(err)
        os.Exit(1)
    }
	fmt.Println(len(images))
	NX := int(32)
	NY := int(32)
	NTILES = int(math.Pow(2, math.Ceil(math.Log2(math.Max(float64(NX), float64(NY))))))
	TILESIZE = int(256)
	fmt.Printf("%+v tiles, %+v maxzoom, %+v maxsize\n", NTILES, math.Sqrt(float64(NTILES)), NTILES*TILESIZE)

	temp := make([]int, 0, NX*NY)
	for i := 0; i < NX*NY; i++ {
    	temp = append(temp, -1)
	}
	temp = process(0, 1000, temp)
	idx = reshape1DTo2D(NY, NX, temp)
	fmt.Println(idx)

	blacklist := make([]int, 0)
	fmt.Println(blacklist)

	http.HandleFunc("/map/", MainHandler)
	http.HandleFunc("/info/", InfoHandler)
	http.HandleFunc("/black/", BlackHandler)
	http.Handle("/", http.FileServer(http.Dir(*root)))
	log.Println("Listening on 8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func MainHandler(w http.ResponseWriter, r *http.Request) {
	x, y, z, inv := 0, 0, 0, 0
	q := r.URL.Query()
	if(len(q.Get("x")) != 0) {
		x, err = strconv.Atoi(q["x"][0])
	}
	if(len(q.Get("y")) != 0) {
        y, err = strconv.Atoi(q["y"][0])
    }
	if(len(q.Get("z")) != 0) {
        z, err = strconv.Atoi(q["z"][0])
    }
	if(len(q.Get("inv")) != 0) {
        z, err = strconv.Atoi(q["inv"][0])
    }
	if(err != nil) {
		log.Fatal(err)
	}
	fmt.Printf("x = %d, y = %d, z = %d, inv = %d\n", x, y, z, inv)

	new_im := image.NewRGBA(image.Rect(0, 0, TILESIZE, TILESIZE))
	new_color := color.RGBA{0, 100, 0, 255}
	draw.Draw(new_im, new_im.Bounds(), &image.Uniform{new_color}, image.ZP, draw.Src)

	itiles := int(NTILES/(2^z))
	var resize_dim uint
	resize_dim = uint(TILESIZE/int(itiles))
	x_off := 0

	for ix := 1; ix <= itiles; ix++ {
		y_off := 0
		for iy := 1; iy <= itiles; iy++ {
			ic := idx[iy+itiles*y][ix+itiles*x]
			if ic == -1 {
				continue;
			}
			file, err := os.Open(images[ic])
			if err != nil {
    			log.Fatal(err)
			}

			im, err := png.Decode(file)
			if err != nil {
    			log.Fatal(err)
			}
			file.Close()

			resized_im := resize.Resize(resize_dim , resize_dim, im, resize.Lanczos3)
			start_point := image.Point{x_off, y_off}
			new_rect := image.Rectangle{start_point, start_point.Add(im.Bounds().Size())}

			draw.Draw(new_im, new_rect, resized_im, image.Point{0,0}, draw.Src)

			y_off += int(resize_dim)
		}
		x_off += int(resize_dim)
	}

	var img image.Image = new_im
	writeImage(w, &img)
}

func process(start int, stop int, slice []int) []int {
	newSlice := slice
	for i := 0; i < stop; i++ {
		newSlice[i] = i
	}
	return newSlice
}

func reshape1DTo2D(dim1 int, dim2 int, slice []int) [][]int {
	newArr := make([][]int, dim1)
    for i := 0; i < dim1; i++ {
    	newArr[i] = make([]int, dim2)

		for j := 0; j < dim2; j++ {
			newArr[i][j] = slice[i*32 + j]
		}
	}
	return newArr
}


func InfoHandler(w http.ResponseWriter, r *http.Request) {
}

func BlackHandler(w http.ResponseWriter, r *http.Request) {
}

// writeImage encodes an image 'img' in jpeg format and writes it into ResponseWriter.
func writeImage(w http.ResponseWriter, img *image.Image) {
	buffer := new(bytes.Buffer)
	if err := jpeg.Encode(buffer, *img, nil); err != nil {
		log.Println("unable to encode image.")
	}

	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("Content-Length", strconv.Itoa(len(buffer.Bytes())))
	if _, err := w.Write(buffer.Bytes()); err != nil {
		log.Println("unable to write image.")
	}
}
