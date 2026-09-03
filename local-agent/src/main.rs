use axum::{
    extract::{Path, State},
    http::{header::CONTENT_TYPE, Method, StatusCode},
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::{env, fs, net::SocketAddr, path::PathBuf, process::Command, sync::Arc};
use tower_http::cors::{Any, CorsLayer};

#[derive(Debug, Clone, Deserialize, Serialize)]
struct GameEntry {
    id: String,
    name: String,
    executable: String,
    #[serde(default)]
    args: Vec<String>,
    working_dir: Option<String>,
    #[serde(default = "default_enabled")]
    enabled: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
struct GameCatalog {
    #[serde(default)]
    games: Vec<GameEntry>,
}

#[derive(Debug, Serialize)]
struct PublicGameEntry {
    id: String,
    name: String,
}

#[derive(Debug, Serialize)]
struct PublicCatalog {
    games: Vec<PublicGameEntry>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
struct DeviceCredentials {
    server_url: String,
    device_id: String,
    device_token: String,
}

#[derive(Clone)]
struct AppState {
    catalog_path: Arc<PathBuf>,
    device_path: Arc<PathBuf>,
    client: Client,
}

#[derive(Serialize)]
struct HealthResponse {
    ok: bool,
    name: &'static str,
    version: &'static str,
    bind: &'static str,
    paired: bool,
}

#[derive(Serialize)]
struct CapabilitiesResponse {
    os: &'static str,
    arch: &'static str,
    logical_cpus: usize,
    rendering: &'static str,
    execution: &'static str,
    arbitrary_commands: bool,
    pairing: &'static str,
}

#[derive(Deserialize)]
struct PairRequest {
    server_url: String,
    ticket: String,
    name: Option<String>,
}

#[derive(Serialize)]
struct PairServerRequest {
    ticket: String,
    name: String,
    os: &'static str,
    arch: &'static str,
    logical_cpus: usize,
}

#[derive(Deserialize)]
struct PairServerResponse {
    device_id: String,
    device_token: String,
}

#[derive(Serialize)]
struct PairResponse {
    ok: bool,
    device_id: String,
}

#[derive(Deserialize)]
struct LaunchRequest {
    ticket: String,
}

#[derive(Serialize)]
struct ConsumeLaunchRequest {
    ticket: String,
    game_id: String,
}

#[derive(Serialize)]
struct LaunchResponse {
    ok: bool,
    game_id: String,
    pid: u32,
}

fn default_enabled() -> bool {
    true
}

#[tokio::main]
async fn main() {
    let catalog_path = env::var("STORCLOUD_AGENT_GAMES")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("config/games.json"));
    let device_path = env::var("STORCLOUD_AGENT_DEVICE")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("config/device.json"));

    let cors = CorsLayer::new()
        .allow_methods([Method::GET, Method::POST])
        .allow_headers([CONTENT_TYPE])
        .allow_origin(Any);

    let state = AppState {
        catalog_path: Arc::new(catalog_path),
        device_path: Arc::new(device_path),
        client: Client::new(),
    };

    let heartbeat_state = state.clone();
    tokio::spawn(async move {
        loop {
            let _ = send_heartbeat(&heartbeat_state).await;
            tokio::time::sleep(std::time::Duration::from_secs(60)).await;
        }
    });

    let app = Router::new()
        .route("/health", get(health))
        .route("/capabilities", get(capabilities))
        .route("/games", get(list_games))
        .route("/pair", post(pair))
        .route("/heartbeat", post(heartbeat))
        .route("/launch/{game_id}", post(launch_game))
        .with_state(state)
        .layer(cors);

    let addr = SocketAddr::from(([127, 0, 0, 1], 47831));
    println!("[StorCloud Agent] listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await.expect("bind local agent");
    axum::serve(listener, app).await.expect("serve local agent");
}

async fn health(State(state): State<AppState>) -> Json<HealthResponse> {
    Json(HealthResponse {
        ok: true,
        name: "StorCloud Local Agent",
        version: env!("CARGO_PKG_VERSION"),
        bind: "127.0.0.1:47831",
        paired: load_device(&state.device_path).is_ok(),
    })
}

async fn capabilities() -> Json<CapabilitiesResponse> {
    Json(CapabilitiesResponse {
        os: env::consts::OS,
        arch: env::consts::ARCH,
        logical_cpus: std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1),
        rendering: "local-device-gpu",
        execution: "native-allowlist",
        arbitrary_commands: false,
        pairing: "server-ticket",
    })
}

async fn list_games(State(state): State<AppState>) -> impl IntoResponse {
    match load_catalog(&state.catalog_path) {
        Ok(catalog) => {
            let games = catalog
                .games
                .into_iter()
                .filter(|game| game.enabled)
                .map(|game| PublicGameEntry { id: game.id, name: game.name })
                .collect();
            (StatusCode::OK, Json(PublicCatalog { games })).into_response()
        }
        Err(_) => (StatusCode::INTERNAL_SERVER_ERROR, "catalog unavailable").into_response(),
    }
}

async fn pair(State(state): State<AppState>, Json(body): Json<PairRequest>) -> impl IntoResponse {
    let server_url = body.server_url.trim_end_matches('/').to_string();
    if !(server_url.starts_with("http://") || server_url.starts_with("https://")) {
        return (StatusCode::BAD_REQUEST, "invalid server url").into_response();
    }

    let request = PairServerRequest {
        ticket: body.ticket,
        name: body.name.unwrap_or_else(|| format!("{}-{}", env::consts::OS, env::consts::ARCH)),
        os: env::consts::OS,
        arch: env::consts::ARCH,
        logical_cpus: std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1),
    };

    let response = match state
        .client
        .post(format!("{server_url}/api/agent/pair"))
        .json(&request)
        .send()
        .await
    {
        Ok(response) if response.status().is_success() => response,
        Ok(response) => return (StatusCode::BAD_GATEWAY, format!("pair rejected by server: {}", response.status())).into_response(),
        Err(error) => return (StatusCode::BAD_GATEWAY, format!("cannot reach StorCloud: {error}")).into_response(),
    };

    let paired: PairServerResponse = match response.json().await {
        Ok(value) => value,
        Err(error) => return (StatusCode::BAD_GATEWAY, format!("invalid server response: {error}")).into_response(),
    };

    let credentials = DeviceCredentials {
        server_url,
        device_id: paired.device_id.clone(),
        device_token: paired.device_token,
    };
    if let Err(error) = save_device(&state.device_path, &credentials) {
        return (StatusCode::INTERNAL_SERVER_ERROR, format!("cannot save device credentials: {error}")).into_response();
    }
    let _ = send_heartbeat(&state).await;

    (StatusCode::OK, Json(PairResponse { ok: true, device_id: paired.device_id })).into_response()
}

async fn heartbeat(State(state): State<AppState>) -> impl IntoResponse {
    match send_heartbeat(&state).await {
        Ok(_) => (StatusCode::OK, "ok").into_response(),
        Err(error) => (StatusCode::BAD_GATEWAY, error).into_response(),
    }
}

async fn launch_game(
    State(state): State<AppState>,
    Path(game_id): Path<String>,
    Json(body): Json<LaunchRequest>,
) -> impl IntoResponse {
    let credentials = match load_device(&state.device_path) {
        Ok(value) => value,
        Err(_) => return (StatusCode::PRECONDITION_REQUIRED, "agent is not paired").into_response(),
    };

    let catalog = match load_catalog(&state.catalog_path) {
        Ok(catalog) => catalog,
        Err(error) => return (StatusCode::INTERNAL_SERVER_ERROR, format!("catalog error: {error}")).into_response(),
    };
    let Some(game) = catalog.games.into_iter().find(|game| game.id == game_id && game.enabled) else {
        return (StatusCode::NOT_FOUND, "game not found or disabled").into_response();
    };
    if !PathBuf::from(&game.executable).is_file() {
        return (StatusCode::BAD_REQUEST, "configured executable does not exist").into_response();
    }

    let validation = state
        .client
        .post(format!("{}/api/agent/launch/consume", credentials.server_url))
        .bearer_auth(&credentials.device_token)
        .json(&ConsumeLaunchRequest { ticket: body.ticket, game_id: game.id.clone() })
        .send()
        .await;

    match validation {
        Ok(response) if response.status().is_success() => {}
        Ok(response) => return (StatusCode::UNAUTHORIZED, format!("launch ticket rejected: {}", response.status())).into_response(),
        Err(error) => return (StatusCode::BAD_GATEWAY, format!("cannot validate launch ticket: {error}")).into_response(),
    }

    let mut command = Command::new(&game.executable);
    command.args(&game.args);
    if let Some(working_dir) = &game.working_dir {
        command.current_dir(working_dir);
    }

    match command.spawn() {
        Ok(child) => (
            StatusCode::OK,
            Json(LaunchResponse { ok: true, game_id: game.id, pid: child.id() }),
        )
            .into_response(),
        Err(error) => (StatusCode::INTERNAL_SERVER_ERROR, format!("launch failed: {error}")).into_response(),
    }
}

async fn send_heartbeat(state: &AppState) -> Result<(), String> {
    let credentials = load_device(&state.device_path)?;
    let response = state
        .client
        .post(format!("{}/api/agent/heartbeat", credentials.server_url))
        .bearer_auth(&credentials.device_token)
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if response.status().is_success() {
        Ok(())
    } else {
        Err(format!("heartbeat rejected: {}", response.status()))
    }
}

fn load_catalog(path: &PathBuf) -> Result<GameCatalog, String> {
    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    serde_json::from_str(&raw).map_err(|error| error.to_string())
}

fn load_device(path: &PathBuf) -> Result<DeviceCredentials, String> {
    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    serde_json::from_str(&raw).map_err(|error| error.to_string())
}

fn save_device(path: &PathBuf, credentials: &DeviceCredentials) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let raw = serde_json::to_string_pretty(credentials).map_err(|error| error.to_string())?;
    fs::write(path, raw).map_err(|error| error.to_string())
}
