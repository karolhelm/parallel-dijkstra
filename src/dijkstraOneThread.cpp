#include <vector>
#include <iostream>
#include <queue>
#include <climits>

using namespace std;

struct edge{
    int v;
    int val;
};
struct node
{
    int v;
    long long dist;
    bool operator<(const node& other) const {
        return dist > other.dist;
    }
};

// we want to go from 0 to n - 1 

int main(){
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    long long INF = LLONG_MAX;
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
        priority_queue<node> q;
        vector<long long> distance(n, INF); 
        q.push({0, 0});
        distance[0] = 0;
        while(!q.empty()){
            node act = q.top();
            q.pop();
            if(act.dist > distance[act.v]){ 
                continue;           //opt
            }
            if (act.v == n - 1) {
                break;              //opt
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
        if(distance[n - 1] == LLONG_MAX){
            cout << -1 << "\n";
        }else{
            cout << distance[n - 1] << "\n";
        }
        z--;
    }
}