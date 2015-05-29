
import dxfgrabber
import svgwrite
import math


dxf = dxfgrabber.readfile("map.dxf")
svg = svgwrite.Drawing()


class Line(object):

    def __init__(self, letter, dxf_color):
        self.letter = letter
        self.dxf_color = dxf_color
        self.line_svg_layer = svg.g(id="line-" + letter)
        self.hollow_svg_layer = svg.g(id="line-" + letter + "-hollow")


# We use DXF colors as a proxy for line designation.
# These don't actually match the colors we use in the final
# rendered map.
# The order in this list dictates the layering order in the
# map rendering, with the first item deepest.
line_stack = [
    Line("T", 1),
    Line("L", 9),
    Line("A", 5),
    Line("B", 3),
    Line("K", 2),
    Line("R", 40),
    Line("U", 56),
    Line("S", 6),
    Line("V", 211),
    Line("E", 253),
    Line("F", 136),
    Line("J", 176),
    Line("N", 8),
]

line_by_dxf_color = {}
line_by_letter = {}

for line in line_stack:
    line_by_letter[line.letter] = line
    line_by_dxf_color[line.dxf_color] = line

# We assume that the line thickness is the same as the DXF grid size,
# thus causing concurrent lines to exactly abut one another.
line_thickness = dxf.header["$GRIDUNIT"][0]
station_radius = line_thickness * 0.75 * 0.5

css_file = file("style.css")
css_source = css_file.read()

svg.add(svg.style(css_source))

stationsym = svg.symbol(id="station")
stationsym.add(svg.circle(
    r="%fpx" % (line_thickness * 0.5),
    class_="station",
))
stationsym.add(svg.circle(
    r="%fpx" % station_radius,
    class_="stationhollow",
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
seagrp = svg.g(id="sea")
coastlinegrp = svg.g(id="coastlines")
stngrp = svg.g(id="stations")
transfergrp = svg.g(id="transfers")
transferhollowgrp = svg.g(id="transferhollows")
namegrp = svg.g(id="names")

outergrp.add(seagrp)
outergrp.add(coastlinegrp)
for line in line_stack:
    outergrp.add(line.line_svg_layer)
    outergrp.add(line.hollow_svg_layer)
outergrp.add(stngrp)
outergrp.add(transfergrp)
outergrp.add(transferhollowgrp)
outergrp.add(namegrp)
svg.add(outergrp)

outline_coords = [0, 0, 0, 0]


def px(val):
    return "%fpx" % val


for entity in dxf.entities:
    color = entity.color
    line = line_by_dxf_color.get(color, None)
    vehicleclass = "trolley" if entity.linetype == "DASHED" else "lrv"

    if entity.layer in ("Coastline", "Nature"):
        if isinstance(entity, dxfgrabber.entities.LWPolyline):

            points = list(entity.points)
            points.append(points[0])  # close the path
            bulge = list(entity.bulge)
            bulge.append(0.0)

            path_parts = []
            first = True
            last_bulge = 0
            last_point = (0, 0)
            for point, bulge in zip(points, bulge):
                if first:
                    path_parts.append("M %f,%f" % point)
                    first = False
                else:
                    if last_bulge:
                        delta = (
                            point[0] - last_point[0],
                            point[1] - last_point[1],
                        )
                        length = math.sqrt(delta[0] ** 2 + delta[1] ** 2)
                        radius = abs(length * (last_bulge ** 2 + 1) / last_bulge / 4)
                        path_parts.append("A %f,%f 0 0,%i %f,%f" % (
                            radius, radius,
                            0 if last_bulge < 0 else 1,
                            point[0], point[1],
                        ))
                    else:
                        path_parts.append("L %f,%f" % point)

                last_bulge = bulge
                last_point = point

            path_data = "\n".join(path_parts)
            coastlinegrp.add(svg.path(
                path_data,
                class_="coastline",
            ))
        else:
            #print "Coastline/Nature may only contain polylines, not %r" % entity
            pass
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

        if line is None:
            print "Can't make route drawing for unknown line with color %i" % color
            continue

        path_data = "M %f,%f L %f,%f" % (
            entity.start[0], entity.start[1],
            entity.end[0], entity.end[1],
        )
        line.line_svg_layer.add(svg.path(
            path_data,
            class_="line line-%s %s" % (line.letter, vehicleclass),
            stroke_width="%fpx" % line_thickness,
        ))
        line.hollow_svg_layer.add(svg.path(
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

        if line is None:
            print "Can't make route drawing for unknown line with color %i" % color
            continue

        path_data = "M %f,%f A %f,%f 0 %s,1 %f,%f" % (
            x1, y1,
            entity.radius, entity.radius,
            "1" if large_arc else "0",
            x2, y2,
        )
        line.line_svg_layer.add(svg.path(
            path_data,
            class_="line line-%s %s" % (line.letter, vehicleclass),
            stroke_width="%fpx" % line_thickness,
        ))
        line.hollow_svg_layer.add(svg.path(
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
seagrp.add(svg.rect(
    insert=(outline_coords[0], outline_coords[1]),
    size=(width, height),
    class_="water",
))

outf = open('map.svg', 'w')
svg.write(outf)
