# worldbox_map_creation
Creating maps for the game Worldbox from images, as well as possibly other things in the future

create_map_from_image.py

Description:
	A python script that takes an image and creates a Worldbox Map File (.wbox), with several configurable settings. Requires the PIL (pillow) module.
	
Usage:
	The Github Repository with the script also has a .json file, this is the configuration. running the script will also generate a default configuration file.
	To select which image to use, set "input_file_path" to the path to the image you wish to use (make sure to double any backslashes, i.e \\ instead of \ ), and run the script.
	There are other configuration options such as blacklisting some block types, such as explosives, snowy mountains/hills (which can make some images look bad), etc, as well as 
	things like image scale which is a multiplier for the resolution of the image; setting it to 2 will double the size, whereas 1 will leave it unchanged. This is useful for large
	images (the limit seems to be ~1000x1000 pixels), where the game is likely not to handle maps of that size without freezing.
	This script is meant less for generating actual maps - i.e, terrain - and more on creating actual images, though it can be used for terrain.
	NOTE: due to how the game handles maps, your image may be scaled somewhat to match a proper map size, making the resolution a multiple of 64 should prevent this.
	Also, image sizes below 64x64 will error.
	
