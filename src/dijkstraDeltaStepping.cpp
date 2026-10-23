#include <vector>
#include <iostream>
#include <climits>
#include <map>
#include <atomic>
#include <omp.h>

using namespace std;

long long INF = LLONG_MAX;

struct edge{
    int v;
    int val;
};

struct node{
    int v;
    long long dist;
};

long long deltaStepping(vector<vector<edge>> &graph, long long delta){
    int n = graph.size();
    vector<vector<edge>> light(n), heavy(n);
    for(int u = 0; u < n; ++u){
        for(edge e : graph[u]){
            if(e.val > delta){
                heavy[u].push_back(e);
            }else{
                light[u].push_back(e);
            }
        }
    }

    vector<atomic<int>> added(n);
    vector<atomic<long long>> distance(n); 

    for(int i = 0; i<n; ++i){
        added[i] = 0;
        distance[i] = INF;
    }

    map<long long, vector<node>> buckets;

    vector<vector<node>> push_relaxed_later(omp_get_max_threads());

    auto relaxation = [&](edge e, node ne){
        long long newDist = ne.dist + e.val;
        
        long long oldDist = distance[e.v].load();
        while(newDist < oldDist){
            if(distance[e.v].compare_exchange_weak(oldDist, newDist)){
                push_relaxed_later[omp_get_thread_num()].push_back({e.v, newDist});
                break;
            }
        }
    };

    distance[0] = 0;
    buckets[0].push_back({0, 0});
    while(!buckets.empty()){
        long long curIndex = buckets.begin()->first;
        vector<int> heavyNodes; 

        while(true){ 
            auto it = buckets.find(curIndex);
            if(it == buckets.end()){
                break;
            }

            vector<node> curBucket = move(it->second);   
            buckets.erase(it);

            vector <vector<int>> push_heavy_later(omp_get_max_threads());

            #pragma omp parallel for
            for(node curNode : curBucket){
                if(distance[curNode.v].load() != curNode.dist){
                    continue;
                }
        
                if(heavy[curNode.v].size() > 0){
                    if(added[curNode.v].exchange(1)){
                        push_heavy_later[omp_get_thread_num()].push_back(curNode.v);
                    }
                }

                for(edge l : light[curNode.v]){
                    relaxation(l, curNode);
                }
            }

            for(int t = 0; t<omp_get_max_threads(); ++t){
                for(node v : push_relaxed_later[t]){
                    buckets[v.dist / delta].push_back(v);
                }

                push_relaxed_later[t].clear();


                for(int v : push_heavy_later[t]){
                    heavyNodes.push_back(v);
                }

                push_heavy_later[t].clear();
            }
        }

        long long finalDistance = distance[n - 1].load();
        if(finalDistance != INF && finalDistance / delta == curIndex){
            return finalDistance;
        }

        #pragma omp parallel for
        for(int v : heavyNodes){
            long long distOfV = distance[v].load();

            for(edge h : heavy[v]){
                relaxation(h, {v, distOfV});
            }
        }

        for(int t = 0; t<omp_get_max_threads(); ++t){
            for(node v : push_relaxed_later[t]){
                buckets[v.dist / delta].push_back(v);
            }

            push_relaxed_later[t].clear();
        }
    }

    return distance[n - 1].load();
}
// we want to go from 0 to n - 1 

int main(){
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int z;
    cin >> z;
    while(z > 0){
        int n;
        cin >> n;

        vector<vector<edge>> graph(n);

        int m;
        cin >> m;
        
        long long w = 0;

        for(int i = 0; i < m; i++){
            int u, v, val;
            cin >> u >> v >> val;
            
            edge e;
            e.v = v;
            e.val = val;

            graph[u].push_back(e);
            w += val;
        }

        long long delta = max((long long)1, 2*w/m);
        long long answer = deltaStepping(graph, delta);

        if(answer == INF){
            cout << -1 << "\n";
        }else{
            cout << answer << "\n";
        }

        z--;
    }
}