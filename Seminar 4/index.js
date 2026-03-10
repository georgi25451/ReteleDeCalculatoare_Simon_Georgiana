// callback
// promise
// async await

const posts = [
    {title: "Post One", body: "This is post one"},
    {title: "Post Two", body: "This is post two"}
];

function getPosts(){
    setTimeout(() => {
        let output = [];
        posts.forEach((post) => {
            output.push(post);
        })

        console.log(output);
    }, 1000)
}

function createPost(post, callback){
    setTimeout(() => {
        posts.push(post);
        console.log("Adaugare");
        callback();
    }, 2000)
}

getPosts();
//createPost({title: "Post 3", body: "This is post 3"}, getPosts)

function createPostPromise(post){
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            posts.push(post);
           
            const error = false;

            if (!error)
                resolve();
            else
                reject("Error");

        }, 2000)
    })
}

// try - catch - finally nu merge pe un promise
// createPostPromise({title: "Post 3", body: "This is post 3"})
// .then(getPosts)
// .catch(e => console.log(e))
// .finally(() => console.log("finally"));

const promise1 = Promise.resolve("Hello");
const promise2 = new Promise((resolve, reject) => {
    setTimeout(resolve, 2000, "Bye");
})
const promise3 = fetch("https://jsonplaceholder.typicode.com/users").then(res => res.json())

Promise.all([promise1, promise2, promise3]).then(values => console.log(values));

async function createElem(){
    await createPostPromise({title: "Post 3", body: "This is post 3"});
    getPosts();
}

async function fetchData(){
    const res = await fetch("https://jsonplaceholder.typicode.com/users");
    console.log(res);
    const data = await res.json();
    console.log(data);
}

fetchData();

function* squareGenerator(number){
    while(true){
        yield number * number;
        number *= number;
    }
}

const generator = squareGenerator(2);

console.log(generator.next())
console.log(generator.next())
console.log(generator.next())
console.log(generator.return())
console.log(generator.next())
//console.log(generator.throw())

const btn = document.getElementById("btnId");
if (btn){
    btn.addEventListener("click", function(e){
        e.preventDefault();
        e.stopPropagation();    
        console.log(2);
    })
}


