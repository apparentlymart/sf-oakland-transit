
import dxfgrabber
import svgwrite
import math

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

transfer2sym = svg.symbol(id="transfer2")
transfer2sym.add(svg.rect(
    insert=("0", "%fpx" % -station_radius),
    size=("%fpx" % line_thickness, "%fpx" % (station_radius * 2.0)),
    class_="transfer",
))
svg.add(transfer2sym)

outergrp = svg.g(transform="scale(1,-1)")
linegrp = svg.g(id="lines")
linehollowgrp = svg.g(id="linehollows")
stngrp = svg.g(id="stations")
namegrp = svg.g(id="names")

outergrp.add(linegrp)
outergrp.add(linehollowgrp)
outergrp.add(stngrp)
outergrp.add(namegrp)
svg.add(outergrp)


def px(val):
    return "%fpx" % val


for entity in dxf.entities:
    color = entity.color
    vehicleclass = "trolley" if entity.linetype == "DASHED" else "lrv"
    if isinstance(entity, dxfgrabber.entities.Line):
        path_data = "M %f,%f L %f,%f" % (
            entity.start[0], entity.start[1],
            entity.end[0], entity.end[1],
        )
        linegrp.add(svg.path(
            path_data,
            class_="line line-%d %s" % (color, vehicleclass),
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
            class_="line line-%d %s" % (color, vehicleclass),
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
        elif etype == "TRANSFER2":
            stngrp.add(svg.use(
                transfer2sym,
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

outf = open('map.svg', 'w')
svg.write(outf)
