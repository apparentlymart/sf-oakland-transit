
import dxfgrabber
import svgwrite
import math

# We use DXF colors as a proxy for line designation.
# These don't necessarily match the colors we'll use in the final
# rendered map, but they are kept close for ease of editing.
line_color_map = {
    5: "A",
    3: "B",
    7: "G",
    2: "K",
    6: "S",
    1: "T",
    56: "U",
    211: "V",
    40: "R",
    4: "C",
    253: "E",
    136: "F",
    176: "J",
    9: "L",
    16: "M",
    8: "N",
    216: "O",
}

dxf = dxfgrabber.readfile("map.dxf")
svg = svgwrite.Drawing()

# We assume that the line thickness is the same as the DXF grid size,
# thus causing concurrent lines to exactly abut one another.
line_thickness = dxf.header["$GRIDUNIT"][0]
station_radius = line_thickness * 0.75 * 0.5

css_file = file("style.css")
css_source = css_file.read()

svg.add(svg.style(css_source))

stationsym = svg.symbol(id="station")
stationsym.add(svg.circle(
    r="%fpx" % station_radius,
    class_="station",
))
svg.add(stationsym)

stopsym = svg.symbol(id="stop")
stopsym.add(svg.rect(
    insert=("%fpx" % (-station_radius / 4.0), "%fpx" % -station_radius),
    size=("%fpx" % (station_radius * 0.5), "%fpx" % (station_radius * 2.0)),
    class_="stop",
))
svg.add(stopsym)

outergrp = svg.g(transform="scale(1,-1)")
linegrp = svg.g(id="lines")
linehollowgrp = svg.g(id="linehollows")
stngrp = svg.g(id="stations")
transfergrp = svg.g(id="transfers")
transferhollowgrp = svg.g(id="transferhollows")
namegrp = svg.g(id="names")

outergrp.add(linegrp)
outergrp.add(linehollowgrp)
outergrp.add(stngrp)
outergrp.add(transfergrp)
outergrp.add(transferhollowgrp)
outergrp.add(namegrp)
svg.add(outergrp)


def px(val):
    return "%fpx" % val


outline_coords = [0, 0, 0, 0]


for entity in dxf.entities:
    color = entity.color
    line_letter = line_color_map.get(color, "invalid")
    vehicleclass = "trolley" if entity.linetype == "DASHED" else "lrv"

    if entity.layer in ("Coastline", "Nature"):
        # Don't know how to render these yet
        continue

    if isinstance(entity, dxfgrabber.entities.Line):
        if entity.layer == "Transfers":
            # Lines on the "Transfers" layer become transfer paths rather
            # than line shapes.
            path_data = "M %f,%f L %f,%f" % (
                entity.start[0], entity.start[1],
                entity.end[0], entity.end[1],
            ),
            transfergrp.add(svg.path(
                path_data,
                class_="transfer",
                stroke_width="%fpx" % (line_thickness),
            ))
            transferhollowgrp.add(svg.path(
                path_data,
                class_="transferhollow",
                stroke_width="%fpx" % (station_radius * 2.0),
            ))
            continue

        if entity.layer == "Outline":
            for coord in (entity.start, entity.end):
                if coord[0] < outline_coords[0]:
                    outline_coords[0] = coord[0]
                if coord[1] < outline_coords[1]:
                    outline_coords[1] = coord[1]
                if coord[0] > outline_coords[2]:
                    outline_coords[2] = coord[0]
                if coord[1] > outline_coords[3]:
                    outline_coords[3] = coord[1]
            continue

        path_data = "M %f,%f L %f,%f" % (
            entity.start[0], entity.start[1],
            entity.end[0], entity.end[1],
        )
        linegrp.add(svg.path(
            path_data,
            class_="line line-%s %s" % (line_letter, vehicleclass),
            stroke_width="%fpx" % line_thickness,
        ))
        linehollowgrp.add(svg.path(
            path_data,
            class_="linehollow linehollow-%d %s" % (color, vehicleclass),
        ))
    elif isinstance(entity, dxfgrabber.entities.Arc):
        # SVG arcs work pretty differently than DXF arcs, so we need
        # do a bit of trigonometry here.
        startangle_rad = math.radians(entity.startangle)
        endangle_rad = math.radians(entity.endangle)
        x1 = entity.center[0] + entity.radius * math.cos(startangle_rad)
        y1 = entity.center[1] + entity.radius * math.sin(startangle_rad)
        x2 = entity.center[0] + entity.radius * math.cos(endangle_rad)
        y2 = entity.center[1] + entity.radius * math.sin(endangle_rad)
        if entity.endangle < entity.startangle:
            entity.endangle += 360.0
        large_arc = (entity.endangle - entity.startangle) > 180

        path_data = "M %f,%f A %f,%f 0 %s,1 %f,%f" % (
            x1, y1,
            entity.radius, entity.radius,
            "1" if large_arc else "0",
            x2, y2,
        )
        linegrp.add(svg.path(
            path_data,
            class_="line line-%s %s" % (line_letter, vehicleclass),
            stroke_width="%fpx" % line_thickness,
        ))
        linehollowgrp.add(svg.path(
            path_data,
            class_="linehollow linehollow-%d %s" % (color, vehicleclass),
        ))
    elif isinstance(entity, dxfgrabber.entities.Insert):
        etype = entity.name
        rotation = entity.rotation
        if etype == "STATION":
            stngrp.add(svg.use(
                stationsym,
                insert=(px(entity.insert[0]), px(entity.insert[1])),
                transform="rotate(%f %f %f)" % (rotation, entity.insert[0], entity.insert[1]),
            ))
        elif etype == "STOP":
            stngrp.add(svg.use(
                stopsym,
                insert=(px(entity.insert[0]), px(entity.insert[1])),
                transform="rotate(%f %f %f)" % (rotation, entity.insert[0], entity.insert[1]),
            ))
        else:
            print "Unknown entity type %r" % etype
    elif isinstance(entity, dxfgrabber.entities.Text):
        if entity.halign == 0:
            halign = "start"
        elif entity.halign == 2:
            halign = "end"
        else:
            halign = "middle"
        textelem = svg.text(
            text="",
            x=[px(entity.insert[0])],
            y=[px(-entity.insert[1])],
            class_="name",
            transform="scale(1,-1)",
            style="text-anchor: %s;font-size:%fpx;" % (
                halign,
                entity.height * 1.1,
            ),
        )
        textelem.add(svg.tspan(
            text=entity.text,
            # SVG doesn't support vertical alignment of text so we arrived
            # at this coefficient experimentally to put the text in approx.
            # the right place relative to its original insertion point.
            dy=["%fpx" % (entity.height * 0.4)],
        ))
        namegrp.add(textelem)
    else:
        print "Don't know what to do with %r" % entity

width = outline_coords[2] - outline_coords[0]
height = outline_coords[3] - outline_coords[1]
svg.attribs["viewBox"] = "%f %f %f %f" % (
    outline_coords[0], outline_coords[1],
    width, height,
)

outf = open('map.svg', 'w')
svg.write(outf)
