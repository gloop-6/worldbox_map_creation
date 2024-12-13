import json,zlib,logging,sys
from pathlib import Path
from os import getenv,path
from configparser import RawConfigParser
from typing import Any
from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt6 import QtWidgets as wdg
from PyQt6 import QtCore as core
from PyQt6.QtGui import QPixmap,QIcon
import PyQt6.QtWidgets as wdg

logger = logging.getLogger("Image_to_map")
#i haven't really messed with logging before, this is just in case for now
#will improve later
logging.basicConfig(filename="imgtomap.log", encoding="utf-8",format="[%(levelname)s]:%(message)s", level=logging.DEBUG)

PREVIEW_SIZE = 200,200
default_image_folder = Path.home() / "Pictures"
env = path.dirname(getenv('APPDATA'))
default_wbox_save_folder = env+"/LocalLow/mkarpenko/WorldBox/saves/save6/map.wbox"
filepath_out = r"c:\Users\gloop\AppData\LocalLow\mkarpenko\WorldBox\saves\save6\map.wbox"

main_cfg_fp = r"main.cfg"
CHUNK_SIZE = 64
DEFAULT_RES = 4,4
res = [DEFAULT_RES[0],DEFAULT_RES[1]] #avoiding directly referencing it, since this is going to be mutated
res_tiles = [res[0]*CHUNK_SIZE,res[1]*CHUNK_SIZE]
window_size = 500,700


def hex_to_rgb(h:str)->list[int,int,int]:
    l = [int(h[i : i + 2], 16) for i in range(0, 6, 2)]
    return l

def flatten(l:list)->list: return [i for sublist in l for i in sublist]

def quantize_to_palette(
    im:Image.Image,
    colors:list[list[int,int,int]],
    dither:bool=True
)->Image.Image:
    if len(colors):
        colors_flat = flatten(colors)
        p_img = Image.new('P', (1, 1))
        p_img.putpalette(colors_flat)
        if im.mode != "RGB": im = im.convert("RGB")
        im = im.quantize(palette=p_img, dither=dither)
        return im
    else:
        print("Error: List of colors is empty!")
def update_resolution(r:list[int,int]) -> None:
    #i guess mutating is better than globals
    res[0]=max(1,r[0])
    res[1]=max(1,r[1])
    res_tiles[0] = res[0]*CHUNK_SIZE
    res_tiles[1] = res[1]*CHUNK_SIZE


update_resolution(DEFAULT_RES)

tile_palette = {}
tile_categories = {}
tile_names = {}
tile_names_reverse = {}
world_ages = {}
world_laws = {}
world_stats = {}
stylesheets = RawConfigParser()
main_cfg = RawConfigParser()

def config_to_dict(c):
    d = {}
    for name,vals in c.items():
        l = {}
        for k,v in vals.items():
            l[k]=v
        d[name]=l
    return d

def load_configs() -> None:
    main_cfg.clear()
    main_cfg.read(main_cfg_fp)
    defs = main_cfg["Definition Files"]

    stylesheets.clear()
    stylesheets.read(defs["stylesheets"])

    world_stats.clear()
    for k,v in main_cfg["World Stats"].items(): world_stats[k]=v

    world_laws.clear()
    for k,v in main_cfg["World Laws"].items(): world_laws[k]=v

    world_ages.clear()
    for k,v in main_cfg["World Ages"].items(): world_ages[k]=v

    with open(defs["tile_types"]) as f:
        tile_data = f.read()
        json_data = json.loads(tile_data)
        tile_palette.clear()
        for k,v in json_data.items():
            tile_palette[k] = v

    with open(defs["tile_categories"]) as f:
        tile_data = f.read()
        tile_categories.clear()
        json_data = json.loads(tile_data)
        for k,v in json_data.items():
            tile_categories[k] = v

    with open(defs["tile_names"]) as f:
        tile_data = f.read()
        json_data = json.loads(tile_data)
        tile_names.clear()
        tile_names_reverse.clear()
        for k,v in json_data.items():
            tile_names[k] = v
            tile_names_reverse[v] = k

load_configs()

im = Image.new("RGB",res_tiles)
tiles_enabled_disabled = {}
tilemap = list(tile_palette.keys())

def generate_tile_data(data:list[int],res:list[int,int]) -> tuple[list,list]:
    """
    Returns a list of tile IDs and tile counts from an array of indices.  
    The format uses tilemap as a palette, then each tile ID is an index in that palette.  
    It's run-length encoded into two arrays, one for the tile IDs and one for the amount of those tiles.
    """
    tile_ids,tile_amts = [],[] #rows
    previous_tile = None

    ids,amts = [],[] #entries within a row
    total_amt = 0 #total amount of tiles
    data_len = res[0]*res[1]

    assert len(data)==data_len, f"length of data array is {len(data)}: should be {data_len}"

    for idx,tile in enumerate(data):
        if not idx & 15:
            window.loading_bar.setValue(int((idx/data_len)*90))

        if total_amt==res[0]: #end of row 
            tile_ids.append(ids)
            tile_amts.append(amts)
            ids,amts = [tile],[0]
            total_amt = 0

        if tile != previous_tile: #new tile, reset count
            ids.append(tile)
            amts.append(1)
        else: amts[-1] += 1

        previous_tile = tile 
        total_amt += 1

    tile_ids.append(ids)
    tile_amts.append(amts)

    assert len(tile_ids) == len(tile_amts) == res[1] , f"Tilearray size is {len(tile_ids)}: should be {res[1]}"

    return tile_ids,tile_amts

def generate_map_data(
    tilemap:list[str],
    tile_data:tuple[list,list],
) -> dict[str,Any]:
    laws = [{"name": "world_law_"+k,"boolVal":v} for k,v in world_laws.items()]
    laws += [{"name": "age_"+k,"boolVal":v} for k,v in world_ages.items()]
    tiles,tile_amts = tile_data
    map_data = {
        "saveVersion":main_cfg["Misc."]["save_version"],
        "width":res[0],"height":res[1],
        "mapStats":world_stats,
        #should probably add a selector for these, like for world laws
        "worldLaws":{ 
            "list":laws
        },
        "tilemap":tilemap,#+["mountains"]*(128-len(tilemap)),
        "tileArray":tiles,
        "tileAmounts":tile_amts,
        "fire":[],#*maybe* add fire, but probably not in this
        "frozen_tiles":[],#same thing for this too
        "tiles" : [],#no clue what this does, even really old versions of the save format don't utilize this
        #only leaving it in for posterity
        "cities" : [],#these last four, besides maybe buildings, are likely out of the scope of this tool
        "actors" : [],
        "buildings" : [],
        "kingdoms" : []
    }
    return map_data

tiles_enabled_disabled = {k:True for k in tilemap}
def get_tile_colors()->tuple[list,list]:
    tile_colors= []
    tiles_enabled = []
    for k,v in tiles_enabled_disabled.items():
        if v:
            col = tile_palette.get(k,"ff00ff")#fallback color in case of invalid tile
            tile_colors.append(hex_to_rgb(col))
            tiles_enabled.append(k)
    return tile_colors,tiles_enabled

class MainWindow(wdg.QMainWindow):

    def __init__(self):
        super().__init__()
        self.use_dither = True
        self.setWindowTitle("Worldbox - Image To Map")
        icon_path = path.join(main_cfg["Definition Files"]["icons_folder"],"wbox_image_to_map.ico")
        icon_path = icon_path.replace("\\","/")
        self.setWindowIcon(QIcon(icon_path))
        self.setStyleSheet(stylesheets["All"]["window"]) 
        self.img_preview = im.resize(PREVIEW_SIZE)
        self.img_main = im
        main = wdg.QFrame()

        main.setFrameStyle(0x40)
        main.setFrameShape(wdg.QFrame.Shape.Box)

        self.layout_main = wdg.QVBoxLayout(main)
        main.setLayout(self.layout_main)
        filesel = wdg.QFileDialog(self)
        filesel.setVisible(False)
        self.setCentralWidget(main)

        self.img_display_lbl = wdg.QLabel("")
        self.img_display_lbl.setScaledContents(True)
        self.img_display_lbl.setFixedSize(*PREVIEW_SIZE)
        self.update_image(self.img_main)
        self.layout_main.addWidget(self.img_display_lbl)

        self.init_buttons() #this is just to make __init__ less monolithic
        self.layout_main.addSpacerItem(wdg.QSpacerItem(1,20))
        self.init_res_selector()
        
        self.layout_main.addSpacerItem(wdg.QSpacerItem(1,20))
        self.btn_reload_cfg.setVisible(True)
        self.layout_main.addWidget(self.btn_reload_cfg)

        self.loading_bar = wdg.QProgressBar()
        self.loading_bar.isVisible = False
        self.loading_bar.setStyleSheet(stylesheets["All"]["progress_bar"])
        self.layout_main.addWidget(self.loading_bar)
        dither_chkbox = wdg.QCheckBox(self)
        dither_chkbox.setChecked(True)
        dither_chkbox.setText("Use Dithering")
        dither_chkbox.stateChanged.connect(lambda : self.set_dither(dither_chkbox.isChecked()))
        self.layout_main.addWidget(dither_chkbox)
        self.init_tabs()

    def set_dither(self,b:bool)->None:
        self.use_dither = b
        self.update_image(self.img_main)

    def init_buttons(self)->None:
        self.btn_map_create = wdg.QPushButton("Create Map")
        self.btn_map_create.setFixedSize(80,20)
        self.btn_map_create.clicked.connect(lambda : self.btn_press("create_map"))
        self.btn_map_create.setStyleSheet(stylesheets["All"]["buttons"])
        self.layout_main.addWidget(self.btn_map_create)

        self.btn_map_create = wdg.QPushButton("Open Image")
        self.btn_map_create.setFixedSize(80,20)
        self.btn_map_create.clicked.connect(lambda : self.btn_press("open_image"))
        self.btn_map_create.setStyleSheet(stylesheets["All"]["buttons"])
        self.layout_main.addWidget(self.btn_map_create)

        self.btn_reload_cfg = wdg.QPushButton("Reload Config")
        self.btn_reload_cfg.setFixedSize(80,20)
        self.btn_reload_cfg.clicked.connect(lambda : self.btn_press("reload_cfg"))
        self.btn_reload_cfg.setStyleSheet(stylesheets["All"]["buttons"])

    def enable_disable_category(self,cat:str,b:bool)->None:
        global tiles_enabled_disabled #ugh
        for i in self.chkbox_categories[cat]:
            i.setChecked(b)
            tiles_enabled_disabled[tile_names_reverse[i.text()]] = b
            
        self.update_image(self.img_main)

    def init_res_selector(self)->None:
        nest_wdg = wdg.QFrame()
        nest_wdg.setFixedWidth(102)
        nest_wdg.setFrameStyle(0x40)
        nest_wdg.setFrameShape(wdg.QFrame.Shape.Box)
        res_selector_lbl = wdg.QLabel("Resolution:",nest_wdg)
        res_selector_lbl.setFixedHeight(13)
        self.layout_main.addWidget(res_selector_lbl)
        
        res_box = wdg.QHBoxLayout(nest_wdg)
        res_box.addSpacing(1)

        width_sel = wdg.QSpinBox(nest_wdg)
        width_sel.setFixedSize(36,30)
        width_sel.setRange(1,256)
        width_sel.setValue(DEFAULT_RES[0])
        width_sel.setStyleSheet(stylesheets["All"]["spinbox"])
        width_sel.valueChanged.connect(
            lambda:update_resolution((width_sel.value(),res[1]))
        )
        res_box.addWidget(width_sel)

        height_sel = wdg.QSpinBox(nest_wdg)
        height_sel.setFixedSize(36,30)
        height_sel.setRange(1,256)
        height_sel.setValue(DEFAULT_RES[1])
        height_sel.setStyleSheet(stylesheets["All"]["spinbox"])
        height_sel.valueChanged.connect(
            lambda:update_resolution((res[0],height_sel.value()))
        )
        res_box.addWidget(height_sel,alignment=core.Qt.AlignmentFlag.AlignLeft)
        self.layout_main.addWidget(nest_wdg)

    def init_tabs(self)->None:
        self.tile_buttons = []
        self.chkbox_categories = {}
        self.tabs = wdg.QTabWidget(self)
        self.tabs.setTabPosition(wdg.QTabWidget.TabPosition.South)
        self.tabs.setMovable(True)
        for tab_name,data in tile_categories.items():
            self.chkbox_categories[tab_name] = []
            tiles_list = wdg.QListWidget(self)
            item = wdg.QListWidgetItem("")

            button_wdg = wdg.QWidget(self)
            button_wdg.setFixedHeight(100)
            button_wdg.setVisible(False)
            item_layout = wdg.QHBoxLayout()
        
            enable_all_button = wdg.QPushButton("Enable All")
            enable_all_button.setFixedSize(80,20)
            enable_all_button.setStyleSheet(stylesheets["All"]["buttons"])
            enable_all_button.setObjectName(tab_name)
            enable_all_button.clicked.connect(
                lambda _=tab_name, instance=enable_all_button:
                    self.enable_disable_category(instance.objectName(),True))
            item_layout.addWidget(enable_all_button,alignment=core.Qt.AlignmentFlag.AlignTop)

            disable_all_button = wdg.QPushButton("Disable All")
            disable_all_button.setFixedSize(80,20)
            disable_all_button.setStyleSheet(stylesheets["All"]["buttons"])
            disable_all_button.setObjectName(tab_name)
            disable_all_button.clicked.connect(
                lambda _=tab_name, instance=disable_all_button:
                    self.enable_disable_category(instance.objectName(),False))
            item_layout.addWidget(disable_all_button,alignment=core.Qt.AlignmentFlag.AlignLeft|core.Qt.AlignmentFlag.AlignTop)
            
            button_wdg.setLayout(item_layout)
            tiles_list.addItem(item)
            tiles_list.setItemWidget(item,button_wdg)

            item.setSizeHint(button_wdg.sizeHint())
            for tile_type,enabled in data.items():
                icon_path = path.join(main_cfg["Definition Files"]["tile_images_folder"],tile_type.replace(":","!")+".png")
                icon_pixmap = QPixmap(icon_path)
                if icon_pixmap.isNull():
                    icon_pixmap = QPixmap(path.join(main_cfg["Definition Files"]["icons_folder"],"missing_tile.png"))
                    logger.warning(f'[init_tabs] Tile "{item.text()}"" has no icon.')
                item_icon = QIcon(icon_pixmap)

                tile_name = tile_names.get(tile_type,f"Unknown Tile ({tile_type})")
                box_holder = wdg.QListWidgetItem(tile_name)
                #box_holder
                chkbox = wdg.QCheckBox()
                chkbox.setIcon(item_icon)
                box_holder.setFlags(box_holder.flags() | core.Qt.ItemFlag.ItemIsUserCheckable)
                tiles_enabled_disabled[tile_type]=enabled
                chkbox.setChecked(enabled)
                chkbox.setText(tile_name)
                chkbox.setObjectName(tile_type)
                chkbox.checkStateChanged.connect(lambda _,instance=chkbox:self.on_checkbox_clicked(instance))
                tiles_list.addItem(box_holder)
                tiles_list.setItemWidget(box_holder,chkbox)
                self.tile_buttons.append(chkbox)
                self.chkbox_categories[tab_name].append(chkbox)
            tiles_list.setStyleSheet(stylesheets["All"]["list"])
            #tiles_list.itemChanged.connect(self.on_checkbox_clicked)
            self.tabs.addTab(tiles_list, tab_name)
        self.tabs.setStyleSheet(stylesheets["All"]["tabs"]) 
        self.layout_main.addWidget(self.tabs)

    def open_file_sel(self,mode:str="in")->None|str:#add output select too
        if mode == "in":
            filename, _ = wdg.QFileDialog.getOpenFileName(self, "Open Image", 
                default_image_folder.as_uri(), "Image Files (*.png *.jpg *.bmp)")
            if filename:
                with Image.open(filename) as im:
                    self.update_image(im)
        elif mode == "out":
            ftypes = "Worldbox Save File (*.wbox)"

            filename, _ = wdg.QFileDialog.getSaveFileName(self,"Save Map",default_wbox_save_folder,ftypes,options=wdg.QFileDialog.Option.DontConfirmOverwrite)
            return filename

    def update_image(self,im):
        if im is not self.img_main:
            self.img_main = im
            self.img_preview = self.img_main.resize(PREVIEW_SIZE)
        tile_colors = get_tile_colors()[0]
        
        if tile_colors:
            preview = quantize_to_palette(self.img_preview,tile_colors,dither=self.use_dither)
            im_qt = ImageQt(preview)
            pixmap = QPixmap.fromImage(im_qt)
        else:
            fallback_img_path = path.join(main_cfg["Definition Files"]["icons_folder"],"fallback_preview.png")
            pixmap = QPixmap(fallback_img_path) #display a fallback image

        self.img_display_lbl.setPixmap(pixmap)

    def btn_press(self,btn_type):
        if btn_type == "create_map":
            self.create_map()
        elif btn_type == "open_image":
            self.open_file_sel()
        elif btn_type == "reload_cfg":
            load_configs()
            reload_enabled_tiles()

    def on_checkbox_clicked(self, item):
        tile_type = tile_names_reverse.get(item.text(),None)
        if tile_type is None: #this shouldn't happen unless the config is malformed, i.e an extra tile in tile_categories
            logger.error(f"[on_checkbox_clicked] tile {item.text()} is invalid!")
        else:
            tiles_enabled_disabled[tile_type]=item.isChecked()
            self.update_image(self.img_main)
        
    def create_map(self,compress=True)->Any:
        self.loading_bar.setVisible(True)

        map_img = self.img_main.resize(res_tiles)
        tile_cols,tiles_enabled = get_tile_colors()
        if len(tiles_enabled):
            map_img = quantize_to_palette(map_img,tile_cols,dither=self.use_dither)
            map_img = map_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            tile_data = generate_tile_data(map_img.getdata(),res_tiles)
            map_data = generate_map_data(tiles_enabled,tile_data)
            window.loading_bar.setValue(100)
            out_fp = self.open_file_sel(mode="out")
            if out_fp:
                with open(out_fp,"wb") as f:
                    if compress:
                        f.write(zlib.compress(json.dumps(map_data).encode("utf8")))
                    else:
                        f.write(json.dumps(map_data))
            else:
                logger.error("[create_map] no valid filepath!")
        else:
            logger.error("[create_map] no enabled tiles!")
            wdg.QMessageBox.critical(self, "Error", "No Tiles Selected!")

app = wdg.QApplication([])
window = MainWindow()
window.resize(core.QSize(*window_size))
window.show()

def reload_enabled_tiles():
    global tiles_enabled_disabled

    for val in tile_categories.values():
        for tile_type,enabled in val.items():
            tiles_enabled_disabled[tile_type]=enabled
    for i in window.tile_buttons:
        tile_name = i.text()
        tile_type = tile_names_reverse.get(tile_name,None)
        tile_is_enabled = tiles_enabled_disabled.get(tile_type,None)
        if tile_is_enabled is not None:
            i.setChecked(tile_is_enabled)
app.exec()
