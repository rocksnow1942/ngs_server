import matplotlib.pyplot as plt
import matplotlib.animation as animation
import requests 
import sys

def animateplot(key):
    fig, ax = plt.subplots()

    def newplot(i,):
        r = requests.get(
            url="http://127.0.0.1:5000/api/get_plojo_data", json={'keys': [key]})
        data = r.json()
        c = data[key].get('concentration',[0])
        s = data[key].get('signal',[0])
        ax.clear()
        ax.plot(c, s)
        ax.set_title(f'{key} curve')
        ax.set_xlabel('Time / Minutes')
        ax.set_ylabel('Singal / nA')
    ani = animation.FuncAnimation(fig, newplot, interval=5000)
    plt.show()

if __name__ == "__main__":
    key = sys.argv[-1]
    animateplot(key)


def plottrace(key):
    "plot filgure in another thread."

    def animateplot(key):
        print('Plot called here',)
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()

        def newplot(i,):
            print('Plot called', i)
            r = requests.get(
                url="http://127.0.0.1:5000/api/get_plojo_data", json={'keys': [key]})
            data = r.json()
            c = data[key]['concentration']
            s = data[key]['signal']
            ax.clear()
            ax.plot(c, s)
            ax.set_title(f'{key} curve')
            ax.set_xlabel('Time / Minutes')
            ax.set_ylabel('Singal / nA')
        ani = animation.FuncAnimation(fig, newplot, interval=5000)
        plt.show()

    p = Process(target=animateplot, args=(key,))
    print('Plot called')
    p.start()
    return p


def animateplot(key):
    print('Plot called here',)
    print("animateplot PID", os.getpid())
    try:
        fig, ax = plt.subplots()
    except:
        print('error ploting')
    print('Plot called here',)

    def newplot(i,):
        print('Plot called', i)
        r = requests.get(
            url="http://127.0.0.1:5000/api/get_plojo_data", json={'keys': [key]})
        data = r.json()
        c = data[key]['concentration']
        s = data[key]['signal']
        ax.clear()
        ax.plot(c, s)
        ax.set_title(f'{key} curve')
        ax.set_xlabel('Time / Minutes')
        ax.set_ylabel('Singal / nA')
    ani = animation.FuncAnimation(fig, newplot, interval=5000)
    plt.show()
