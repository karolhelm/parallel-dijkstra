#include <vector>
#include <iostream>
#include <queue>
#include <climits>
#include <chrono>
#include <iomanip>

using namespace std;

struct edge{
    int v;
    int val;
};

struct node{
    int v;
    long long dist;

    bool operator<(const node& other) const {
        return dist > other.dist;
    }
};

vector<long long> dijkstra(vector<vector<edge>> &graph){
    priority_queue<node> q;
    vector<long long> distance(graph.size(), LLONG_MAX);
    q.push({0, 0});
    distance[0] = 0;
    while(!q.empty()){
        node act = q.top();
        q.pop();

        if(act.dist > distance[act.v]){
            continue;
        }

        for(int i = 0; i < graph[act.v].size(); i++){
            int u = act.v;
            int v = graph[u][i].v;
            int val = graph[u][i].val;
            if(distance[v] > act.dist + val){
                distance[v] = distance[u] + val;
                q.push({v, distance[v]});
            }
        }
    }

    return distance;
}

int main(){
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    double benchTime = 0;
    int z;
    cin >> z;
    while(z > 0){
        int n;
        cin >> n;
        vector<vector<edge>> graph(n);
        int m;
        cin >> m;
        for(int i = 0; i < m; i++){
            int u, v, val;
            edge e;
            cin >> u >> v >> val;
            e.v = v;
            e.val = val;
            graph[u].push_back(e);
        }
        auto benchStart = chrono::steady_clock::now();
        vector<long long> distance = dijkstra(graph);
        benchTime += chrono::duration<double>(chrono::steady_clock::now() - benchStart).count();

        for(int v = 0; v < n; ++v){
            if(v > 0) cout << ' ';
            cout << (distance[v] == LLONG_MAX ? -1 : distance[v]);
        }
        cout << "\n";
        z--;
    }
    
    cerr << setprecision(12) << "BENCH_SOLVE " << benchTime << "\n";
}
