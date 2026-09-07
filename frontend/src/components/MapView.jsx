import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Circle,
  useMap,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import L from "leaflet";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

import { useEffect } from "react";


// Fix Leaflet marker icons
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});


// --------------------------------------------------
// MAP CONTROLLER
// --------------------------------------------------

function MapController({
  vehicles,
  selectedVehicle,
}) {
  const map = useMap();

  useEffect(() => {

    if (!vehicles || vehicles.length === 0) {
      return;
    }

    // If vehicle selected
    if (selectedVehicle) {

      const selected = vehicles.find(
        (item) =>
          item.vehicle === selectedVehicle
      );

      if (selected) {

        map.flyTo(
          [
            selected.latitude,
            selected.longitude,
          ],
          12,
          {
            duration: 1.2,
          }
        );

        return;
      }
    }

    // Otherwise fit all vehicles
    const validVehicles = vehicles.filter(
      (item) =>
        Number.isFinite(
          Number(item.latitude)
        ) &&
        Number.isFinite(
          Number(item.longitude)
        )
    );

    if (validVehicles.length === 1) {

      map.setView(
        [
          validVehicles[0].latitude,
          validVehicles[0].longitude,
        ],
        10
      );

    } else if (validVehicles.length > 1) {

      const bounds = L.latLngBounds(
        validVehicles.map((item) => [
          item.latitude,
          item.longitude,
        ])
      );

      map.fitBounds(bounds, {
        padding: [50, 50],
      });
    }

  }, [
    vehicles,
    selectedVehicle,
    map,
  ]);

  return null;
}

function RouteController({ routeGeometry }) {
  const map = useMap();
  useEffect(() => {
    if (routeGeometry?.type !== "LineString" || routeGeometry.coordinates?.length < 2) return;
    map.fitBounds(L.latLngBounds(routeGeometry.coordinates.map(([longitude, latitude]) => [latitude, longitude])), { padding: [50, 50] });
  }, [map, routeGeometry]);
  return null;
}

const startIcon = L.divIcon({ className: "route-marker-icon", html: '<div style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;border:3px solid white;border-radius:50%;background:#16a34a;color:white;font-weight:700;box-shadow:0 1px 5px rgba(0,0,0,.45)">S</div>', iconSize: [30, 30], iconAnchor: [15, 15] });
const destinationIcon = L.divIcon({ className: "route-marker-icon", html: '<div style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;border:3px solid white;border-radius:50%;background:#dc2626;color:white;font-weight:700;box-shadow:0 1px 5px rgba(0,0,0,.45)">E</div>', iconSize: [30, 30], iconAnchor: [15, 15] });


// --------------------------------------------------
// MAP VIEW
// --------------------------------------------------

export default function MapView({
  vehicles = [],
  selectedVehicle = null,
  onSelectVehicle,
  routeHistory = {},
  routeGeometry = null,
  startLocation = "Start location",
  endLocation = "Destination",
  height = "550px",
}) {

  console.log(
    "Vehicle received:",
    vehicles
  );

  // Safety protection
  const safeVehicles = Array.isArray(
    vehicles
  )
    ? vehicles
    : [];

  return (
    <div className="w-full">

      <MapContainer
        center={[
          16.5,
          78.5,
        ]}
        zoom={6}
        scrollWheelZoom={true}
        style={{
          height,
          width: "100%",
          borderRadius: "12px",
        }}
      >

        {/* MAP CONTROLLER */}

        <MapController
          vehicles={safeVehicles}
          selectedVehicle={
            selectedVehicle
          }
        />


        {/* OPEN STREET MAP */}

        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <RouteController routeGeometry={routeGeometry} />

        {routeGeometry?.type === "LineString" && routeGeometry.coordinates?.length > 1 && <>
          <Polyline positions={routeGeometry.coordinates.map(([longitude, latitude]) => [latitude, longitude])} pathOptions={{ color: "#2563eb", weight: 5, opacity: 0.8 }} />
          <Marker position={[routeGeometry.coordinates[0][1], routeGeometry.coordinates[0][0]]} icon={startIcon}><Popup><b>Start</b><br />{startLocation}</Popup></Marker>
          <Marker position={[routeGeometry.coordinates.at(-1)[1], routeGeometry.coordinates.at(-1)[0]]} icon={destinationIcon}><Popup><b>Destination</b><br />{endLocation}</Popup></Marker>
        </>}


        {/* VEHICLE MARKERS */}

        {safeVehicles.map(
          (item, index) => {

            const lat = Number(
              item.latitude
            );

            const lng = Number(
              item.longitude
            );

            if (
              !Number.isFinite(lat) ||
              !Number.isFinite(lng)
            ) {
              return null;
            }

            const isSelected =
              selectedVehicle ===
              item.vehicle;

            const route =
              routeHistory[
                item.vehicle
              ] || [];

            return (
              <div
                key={`${item.vehicle}-${index}`}
              >

                {/* ROUTE HISTORY */}

                {route.length > 1 && (

                  <Polyline
                    positions={route}
                    pathOptions={{
                      color:
                        item.status ===
                        "Online"
                          ? "blue"
                          : "gray",
                      weight: 4,
                      opacity: 0.7,
                    }}
                  />

                )}


                {/* VEHICLE AREA */}

                <Circle
                  center={[
                    lat,
                    lng,
                  ]}
                  radius={
                    isSelected
                      ? 2500
                      : 1000
                  }
                  pathOptions={{
                    color:
                      item.status ===
                      "Online"
                        ? "green"
                        : "red",
                    fillOpacity: 0.08,
                  }}
                />


                {/* MARKER */}

                <Marker
                  position={[
                    lat,
                    lng,
                  ]}
                  eventHandlers={{
                    click: () => {

                      if (
                        onSelectVehicle
                      ) {
                        onSelectVehicle(
                          item.vehicle
                        );
                      }

                    },
                  }}
                >

                  <Popup>

                    <div
                      style={{
                        minWidth:
                          "220px",
                      }}
                    >

                      <h3
                        style={{
                          fontSize:
                            "18px",
                          fontWeight:
                            "bold",
                          marginBottom:
                            "10px",
                        }}
                      >
                        🚚 {item.vehicle}
                      </h3>


                      <p>
                        <strong>
                          Driver:
                        </strong>{" "}
                        {item.driver}
                      </p>


                      <p>
                        <strong>
                          Location:
                        </strong>{" "}
                        {item.location}
                      </p>


                      <p>
                        <strong>
                          Speed:
                        </strong>{" "}
                        {item.speed} km/h
                      </p>


                      <p>
                        <strong>
                          Status:
                        </strong>{" "}

                        <span
                          style={{
                            color:
                              item.status ===
                              "Online"
                                ? "green"
                                : "red",
                            fontWeight:
                              "bold",
                          }}
                        >
                          {item.status}
                        </span>

                      </p>


                      <p>
                        <strong>
                          Latitude:
                        </strong>{" "}
                        {lat.toFixed(6)}
                      </p>


                      <p>
                        <strong>
                          Longitude:
                        </strong>{" "}
                        {lng.toFixed(6)}
                      </p>


                      <p>
                        <strong>
                          Updated:
                        </strong>{" "}
                        {item.updated}
                      </p>

                    </div>

                  </Popup>

                </Marker>

              </div>
            );
          }
        )}

      </MapContainer>

    </div>
  );
}
