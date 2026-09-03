use axum::{
    extract::{Path, State},
    http::{HeaderMap, HeaderValue, Method, StatusCode},
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::{
    env,
    fs,
    net::SocketAddr,
    path::PathBuf,
    process::Command,
    sync::Arc,
};
use tower_http::cors::{AllowOrigin, CorsLayer};

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

fn default_enabled() -> bool {
    true
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
struct GameCatalog {
    #[serde(default)]
    games: Vec<GameEntry>,
}

#[derive(Clone)]
struct AppState {
    token: Arc<String>,
    catalog_path: Arc<PathBuf>,
}

#[derive(Serialize)]
struct HealthResponse {
    ok: bool,
    name: &'static str,
    version: &'static str,
    bind: &'static str,
}

#[derive(Serialize)]
struct CapabilitiesResponse {
    os: &'static str,
    arch: &'static str,
    logical_cpus: usize,
    rendering: &'static str,
    execution: &'static str,
    arbitrary_commands: bool,
}

#[derive(Serialize)]
struct LaunchResponse {
    ok: bool,
    game_id: String,
    pid: u32,
}

#[tokio::main]
async fn main() {
    let token = env::var("STORCLOUD_AGENT_TOKEN").unwrap_or_else(|_| "change-me".to_string());
    if token == "change-me" {
        eprintln!("[StorCloud Agent] WARNING: STORCLOUD_AGENT_TOKEN is using the insecure default. Set a strong token before enabling launches.");
    }

    let catalog_path = env::var("STORCLOUD_AGENT_GAMES")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("config/games.json"));

    let origin_values = env::var("STORCLOUD_ORIGINS")
        .unwrap_or_else(|_| "http://localhost:8080,http://127.0.0.1:8080".to_string())
        .split(',')
        .filter_map(|value| value.trim().parse::<HeaderValue>().ok())
        .collect::<Vec<_>>();

    let cors = CorsLayer::new()
        .allow_methods([Method::GET, Method::POST])
        .allow_headers([
            axum::http::header::AUTHORIZATION,
            axum::http::header::CONTENT_TYPE,
        ])
        .allow_origin(AllowOrigin::list(origin_values));

    let state = AppState {
        token: Arc::new(token),
        catalog_path: Arc::new(catalog_path),
    };

    let app = Router::new()
        .route("/health", get(health))
        .route("/capabilities", get(capabilities))
        .route("/games", get(list_games))
        .route("/launch/{game_id}", post(launch_game))
        .with_state(state)
        .layer(cors);

    let addr = SocketAddr::from(([127, 0, 0, 1], 47831));
    println!("[StorCloud Agent] listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await.expect("bind local agent");
    axum::serve(listener, app).await.expect("serve local agent");
}

async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        ok: true,
        name: "StorCloud Local Agent",
        version: env!("CARGO_PKG_VERSION"),
        bind: "127.0.0.1:47831",
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
    })
}

async fn list_games(State(state): State<AppState>, headers: HeaderMap) -> impl IntoResponse {
    if !authorized(&headers, &state.token) {
        return (StatusCode::UNAUTHORIZED, Json(GameCatalog::default())).into_response();
    }

    match load_catalog(&state.catalog_path) {
        Ok(catalog) => (StatusCode::OK, Json(catalog)).into_response(),
        Err(_) => (StatusCode::INTERNAL_SERVER_ERROR, Json(GameCatalog::default())).into_response(),
    }
}

async fn launch_game(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(game_id): Path<String>,
) -> impl IntoResponse {
    if !authorized(&headers, &state.token) {
        return (StatusCode::UNAUTHORIZED, "unauthorized").into_response();
    }

    let catalog = match load_catalog(&state.catalog_path) {
        Ok(catalog) => catalog,
        Err(error) => {
            return (StatusCode::INTERNAL_SERVER_ERROR, format!("catalog error: {error}")).into_response();
        }
    };

    let Some(game) = catalog.games.into_iter().find(|game| game.id == game_id && game.enabled) else {
        return (StatusCode::NOT_FOUND, "game not found or disabled").into_response();
    };

    if !PathBuf::from(&game.executable).is_file() {
        return (StatusCode::BAD_REQUEST, "configured executable does not exist").into_response();
    }

    let mut command = Command::new(&game.executable);
    command.args(&game.args);
    if let Some(working_dir) = &game.working_dir {
        command.current_dir(working_dir);
    }

    match command.spawn() {
        Ok(child) => (
            StatusCode::OK,
            Json(LaunchResponse {
                ok: true,
                game_id: game.id,
                pid: child.id(),
            }),
        )
            .into_response(),
        Err(error) => (StatusCode::INTERNAL_SERVER_ERROR, format!("launch failed: {error}")).into_response(),
    }
}

fn authorized(headers: &HeaderMap, token: &str) -> bool {
    let expected = format!("Bearer {token}");
    headers
        .get(axum::http::header::AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
        .is_some_and(|value| value == expected)
}

fn load_catalog(path: &PathBuf) -> Result<GameCatalog, String> {
    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    serde_json::from_str(&raw).map_err(|error| error.to_string())
}
